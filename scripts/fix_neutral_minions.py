import logging
import os

from dotenv import load_dotenv

from src.db import (
    get_connection,
    get_match_ids_to_update,
    init_db,
    update_players_matches_neutral_minions,
)
from src.matches import fetch_match_to_fix, participants_to_tuples
from src.rate_limiter import RateLimiter
from src.riot_api import RiotAPI, RiotAPIError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


load_dotenv()
HEADERS = {"X-Riot-Token": os.getenv("RIOT_API_KEY")}
DB_PATH = os.getenv("DB_PATH")


def run_fix():
    rate_limiter = RateLimiter(thresholds=[(20, 1), (100, 120)])
    riot_api = RiotAPI(limiter=rate_limiter, headers=HEADERS)
    conn = get_connection(DB_PATH)

    try:
        logger.info("Initialisation DB")
        init_db(conn)
        conn.commit()

        i = 1
        matches_to_update = get_match_ids_to_update(conn)
        for match_id in matches_to_update:
            logger.info(
                f"Maj neutral_minions_killed du match {match_id}, {i}/{len(matches_to_update)}"
            )
            try:
                data = fetch_match_to_fix(riot_api, match_id)
            except RiotAPIError as e:
                logger.warning(f"Match {match_id} ignoré : {e}")
                continue
            update_players_matches_neutral_minions(conn, participants_to_tuples(data))
            conn.commit()
            i += 1

    finally:
        conn.close()
        logger.info("Run fix terminé")


if __name__ == "__main__":
    run_fix()
