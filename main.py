import logging
import os

from dotenv import load_dotenv

from src.rate_limiter import RateLimiter
from src.riot_api import RiotAPI, RiotAPIError
from src.db import (
    get_connection, init_db, upsert_player, log_ladder_snapshot,
    match_exists, insert_match, insert_players_matches, ensure_player_exists,
    find_active_players, deactivate_players, get_last_match_check, update_last_match_check
)
from src.ladder import fetch_ladder_with_names, ladder_to_player_tuples, ladder_to_history_tuples
from src.matches import (
    fetch_player_matches_ids, fetch_match,
    match_to_tuple, participants_to_tuples, new_players_to_tuples
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


load_dotenv()
HEADERS = {'X-Riot-Token': os.getenv('RIOT_API_KEY')}
DB_PATH = {'X-Riot-Token': os.getenv('DB_PATH')}


def process_ladder(conn, riot_api) -> list[str]:
    try:
        ladder_df = fetch_ladder_with_names(riot_api, 25)

        previously_active = find_active_players(conn)
        currently_active = set(ladder_df['puuid'].tolist())

        to_deactivate = previously_active - currently_active
        if to_deactivate:
            deactivate_players(conn, list(to_deactivate))
            logger.info(f"{len(to_deactivate)} joueur(s) désactivé(s) : {to_deactivate}")

        upsert_player(conn, ladder_to_player_tuples(ladder_df))
        log_ladder_snapshot(conn, ladder_to_history_tuples(ladder_df))
        conn.commit()
        return ladder_df['puuid'].tolist()
    except RiotAPIError as e:
        conn.rollback()
        print(f"Erreur ladder, run annulé : {e}")
        return []


def process_match(conn, riot_api, match_id: str):
    if match_exists(conn, match_id):
        logger.info(f"Match {match_id} - déjà en base, skip")
        return

    try:
        data = fetch_match(riot_api, match_id)

        insert_match(conn, match_to_tuple(data['match_infos']))

        for player_tuple in new_players_to_tuples(data['players_infos']):
            ensure_player_exists(conn, player_tuple)

        insert_players_matches(conn, participants_to_tuples(data['participants_infos']))

        conn.commit()
        logger.info(f"Match {match_id} - inséré")
    except RiotAPIError as e:
        conn.rollback()
        logger.warning(f"Match {match_id} ignoré : {e}")


def run():
    rate_limiter = RateLimiter(thresholds=[(20, 1), (100, 120)])
    riot_api = RiotAPI(limiter=rate_limiter, headers=HEADERS)
    conn = get_connection(DB_PATH)

    try:
        logger.info("Initialisation DB")
        init_db(conn)
        conn.commit()

        active_puuids = process_ladder(conn, riot_api)
        logger.info(f"Ladder récupéré - {len(active_puuids)} joueurs actifs")

        i = 1
        for puuid in active_puuids:
            last_check = get_last_match_check(conn, puuid)

            logger.info(f"Traitement joueur {puuid} ({i}/{len(active_puuids)})")
            try:
                match_ids = fetch_player_matches_ids(riot_api, puuid, start_time=last_check)
            except RiotAPIError as e:
                logger.warning(f"Joueur {puuid} ignoré : {e}")
                continue

            if match_ids:
                logger.info(f"Récupération des {len(match_ids)} matchs du joueur {puuid}")
            for match_id in match_ids:
                process_match(conn, riot_api, match_id)
            i += 1

            update_last_match_check(conn, puuid)

    finally:
        conn.close()
        logger.info("Run terminé")


if __name__ == "__main__":
    run()