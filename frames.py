import csv
import requests
import time

import main as main_module
from main import buscar_puuid, headers, REGION_ROUTING

PUUID = buscar_puuid("Aiolos", "GOLD")
print(f"PUUID: {PUUID}")

MATCH_IDS = main_module.buscar_ids_partidas(PUUID, main_module.QTD_PARTIDAS)


def buscar_match_info(match_id):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return None
    return resp.json()


def buscar_timeline(match_id):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"  Erro ao buscar timeline de {match_id}: {resp.status_code}")
        return None
    return resp.json()


def processar_partida(match_id, puuid):
    match_data = buscar_match_info(match_id)
    if not match_data:
        return []

    participants = match_data["info"]["participants"]

    meu_participant_id = None
    meu_campeao = None
    minha_posicao = None
    meu_time = None
    for p in participants:
        if p["puuid"] == puuid:
            meu_participant_id = p["participantId"]
            meu_campeao = p["championName"]
            minha_posicao = p["teamPosition"]
            meu_time = p["teamId"]
            break

    if meu_participant_id is None:
        print(f"  Jogador não encontrado em {match_id}")
        return []

    adversario_participant_id = None
    campeao_adversario = None
    for p in participants:
        if p["teamPosition"] == minha_posicao and p["teamId"] != meu_time:
            adversario_participant_id = p["participantId"]
            campeao_adversario = p["championName"]
            break

    if adversario_participant_id is None:
        print(f"  Adversário direto não encontrado em {match_id} (posição: {minha_posicao})")
        return []

    time.sleep(1.2)
    timeline_data = buscar_timeline(match_id)
    if not timeline_data:
        return []

    frames = timeline_data["info"]["frames"]

    linhas = []
    for frame in frames:
        minuto = frame["timestamp"] // 60000

        participant_frames = frame["participantFrames"]
        meu_frame = participant_frames.get(str(meu_participant_id))
        adv_frame = participant_frames.get(str(adversario_participant_id))

        if not meu_frame or not adv_frame:
            continue

        meu_gold = meu_frame["totalGold"]
        adv_gold = adv_frame["totalGold"]
        meu_xp = meu_frame["xp"]
        adv_xp = adv_frame["xp"]
        meu_cs = meu_frame["minionsKilled"] + meu_frame["jungleMinionsKilled"]
        adv_cs = adv_frame["minionsKilled"] + adv_frame["jungleMinionsKilled"]

        linhas.append({
            "match_id": match_id,
            "campeao": meu_campeao,
            "campeao_adversario": campeao_adversario,
            "posicao": minha_posicao,
            "minuto": minuto,
            "gold_total_tld": meu_gold,
            "gold_diff": meu_gold - adv_gold,
            "xp_total_tld": meu_xp,
            "xp_diff": meu_xp - adv_xp,
            "cs_total_tld": meu_cs,
            "cs_diff": meu_cs - adv_cs,
            "nivel_tld": meu_frame["level"],
        })

    return linhas


def main():
    todas_as_linhas = []

    for i, match_id in enumerate(MATCH_IDS):
        print(f"[{i+1}/{len(MATCH_IDS)}] Processando timeline de {match_id}...")
        linhas = processar_partida(match_id, PUUID)
        todas_as_linhas.extend(linhas)
        time.sleep(1.2)

    if not todas_as_linhas:
        print("\nNenhum dado coletado.")
        return

    campos = list(todas_as_linhas[0].keys())
    with open("timeline_diff_greggo.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(todas_as_linhas)

    print(f"\nConcluído! {len(todas_as_linhas)} linhas exportadas para timeline_diff_greggo.csv")

    exportar_timeline(todas_as_linhas)


def exportar_timeline(linhas_diff):
    """Gera timeline_greggo.csv (só os totais do jogador) a partir das mesmas partidas."""
    linhas_tl = [
        {
            "match_id": l["match_id"],
            "campeao": l["campeao"],
            "posicao": l["posicao"],
            "minuto": l["minuto"],
            "gold_total_tl": l["gold_total_tld"],
            "xp_total_tl": l["xp_total_tld"],
            "cs_total_tl": l["cs_total_tld"],
            "nivel_tl": l["nivel_tld"],
        }
        for l in linhas_diff
    ]
    with open("timeline_greggo.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(linhas_tl[0].keys()))
        writer.writeheader()
        writer.writerows(linhas_tl)

    print(f"Concluído! {len(linhas_tl)} linhas exportadas para timeline_greggo.csv")


if __name__ == "__main__":
    main()