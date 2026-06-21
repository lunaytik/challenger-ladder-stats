import pandas as pd

from src.riot_api import RiotAPI


def fetch_player_matches_ids(riot_api: RiotAPI, player_puuid: str, start_time: int | None = None):
    url = (
        "https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/"
        + player_puuid
        + "/ids?queue=420&type=ranked"
    )
    if start_time:
        url += f"&startTime={int(start_time)}"
    else:
        url += "&count=20"
    return riot_api.safe_get(url)


def fetch_match(riot_api: RiotAPI, match_id: str):
    url = "https://europe.api.riotgames.com/lol/match/v5/matches/" + match_id
    resp = riot_api.safe_get(url)
    return clean_match_data(resp)


def clean_match_data(response):
    filtered_rows = [
        "puuid",
        "metadata.matchId",
        "kills",
        "assists",
        "deaths",
        "championName",
        "champLevel",
        "champExperience",
        "goldEarned",
        "goldSpent",
        "teamPosition",
        "teamId",
        "totalDamageDealtToChampions",
        "totalMinionsKilled",
        "gameEndedInSurrender",
        "gameEndedInEarlySurrender",
        "visionScore",
        "win",
    ]

    participants_infos = pd.json_normalize(
        response, record_path=[["info", "participants"]], meta=[["metadata", "matchId"]]
    )

    players_infos = participants_infos[["puuid", "riotIdGameName", "riotIdTagline"]]

    participants_infos = participants_infos[filtered_rows]
    participants_infos = participants_infos.rename(columns={"metadata.matchId": "matchId"})

    match_infos = pd.json_normalize(response)
    teams = response["info"]["teams"]
    team_win = next(team["teamId"] for team in teams if team["win"])
    match_infos["team_win"] = team_win

    match_infos = match_infos[
        [
            "metadata.matchId",
            "info.gameVersion",
            "info.gameDuration",
            "team_win",
            "info.gameCreation",
            "info.gameStartTimestamp",
            "info.gameEndTimestamp",
        ]
    ]

    match_infos = match_infos.rename(
        columns={
            "metadata.matchId": "id",
            "info.gameVersion": "game_version",
            "info.gameDuration": "duration",
            "info.gameCreation": "created_at",
            "info.gameStartTimestamp": "started_at",
            "info.gameEndTimestamp": "ended_at",
        }
    )

    return {
        "participants_infos": participants_infos,
        "match_infos": match_infos,
        "players_infos": players_infos,
    }


def match_to_tuple(match_infos_df):
    row = match_infos_df.iloc[0]
    return tuple(
        row[col].item() if hasattr(row[col], "item") else row[col]
        for col in [
            "id",
            "game_version",
            "duration",
            "team_win",
            "created_at",
            "started_at",
            "ended_at",
        ]
    )


def participants_to_tuples(participants_infos_df):
    return [tuple(row) for row in participants_infos_df.itertuples(index=False)]


def new_players_to_tuples(players_infos_df):
    return [
        (row["puuid"], row["riotIdGameName"], row["riotIdTagline"])
        for _, row in players_infos_df.iterrows()
    ]
