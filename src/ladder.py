import pandas as pd

from src.riot_api import RiotAPI


def fetch_ladder_challenger(riot_api: RiotAPI, limit: int = 5):
    url = "https://euw1.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
    resp = riot_api.safe_get(url)
    return clean_ladder_data(resp).head(limit)


def clean_ladder_data(response):
    dataframe = pd.json_normalize(response, record_path="entries", meta=["tier", "queue"])
    return dataframe.sort_values(by="leaguePoints", ascending=False)


def fetch_player_account_name(riot_api: RiotAPI, puuid: str):
    url = "https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/" + puuid
    resp = riot_api.safe_get(url)
    return resp


def fetch_ladder_with_names(riot_api: RiotAPI, limit: int):
    filtered_players = fetch_ladder_challenger(riot_api, limit)
    if filtered_players is None:
        return None

    players_account_infos = []
    for puuid in filtered_players.puuid:
        player_data = fetch_player_account_name(riot_api, puuid)
        players_account_infos.append(
            {
                "puuid": puuid,
                "gameName": player_data["gameName"],
                "tagLine": player_data["tagLine"],
            }
        )
    players_accounts = pd.DataFrame(players_account_infos)

    merged_players = pd.merge(players_accounts, filtered_players, on="puuid", how="left")
    merged_players["in_top"] = True
    return merged_players.drop(columns=["veteran", "inactive", "freshBlood", "hotStreak"])


def ladder_to_player_tuples(players_data):
    return [tuple(row) for row in players_data.itertuples(index=False)]


def ladder_to_history_tuples(players_data):
    ladder_history_data = players_data[["puuid", "leaguePoints", "wins", "losses"]]
    ladder_history_data["rank_position"] = ladder_history_data.index + 1
    return [tuple(row) for row in ladder_history_data.itertuples(index=False)]
