import csv
import math
import time

import main as main_module
from main import buscar_puuid, buscar_ids_partidas, headers, REGION_ROUTING

import requests

# Distância (unidades do mapa) abaixo da qual consideramos o aliado/inimigo "por perto".
# Referência: o mapa tem ~15000 x 15000 unidades e a visão de um campeão é ~1350.
RAIO_PROXIMIDADE = 2000

PAPEIS_ALVO = {"JUNGLE": "Jungle", "UTILITY": "Suporte"}


def buscar_json(url):
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"  Erro {resp.status_code} em {url}")
        return None
    return resp.json()


def distancia(pos_a, pos_b):
    return math.hypot(pos_a["x"] - pos_b["x"], pos_a["y"] - pos_b["y"])


def processar_partida(match_id, puuid):
    match_data = buscar_json(f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}")
    if not match_data:
        return []

    participants = match_data["info"]["participants"]
    eu = next((p for p in participants if p["puuid"] == puuid), None)
    if not eu:
        print(f"  Jogador não encontrado em {match_id}")
        return []

    # Jungle e Suporte de cada time (ignorando o próprio jogador)
    alvos = []
    for p in participants:
        papel = PAPEIS_ALVO.get(p["teamPosition"])
        if papel and p["participantId"] != eu["participantId"]:
            alvos.append({
                "participant_id": p["participantId"],
                "papel": papel,
                "lado": "Aliado" if p["teamId"] == eu["teamId"] else "Inimigo",
                "campeao_alvo": p["championName"],
            })

    time.sleep(1.2)
    timeline = buscar_json(f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline")
    if not timeline:
        return []

    linhas = []
    for frame in timeline["info"]["frames"]:
        minuto = frame["timestamp"] // 60000
        frames = frame["participantFrames"]
        meu_frame = frames.get(str(eu["participantId"]))
        if not meu_frame or "position" not in meu_frame:
            continue

        for alvo in alvos:
            alvo_frame = frames.get(str(alvo["participant_id"]))
            if not alvo_frame or "position" not in alvo_frame:
                continue

            dist = distancia(meu_frame["position"], alvo_frame["position"])
            linhas.append({
                "match_id": match_id,
                "campeao": eu["championName"],
                "posicao": eu["teamPosition"],
                "minuto": minuto,
                "papel": alvo["papel"],
                "lado": alvo["lado"],
                "papel_lado": f"{alvo['papel']} {alvo['lado']}",
                "campeao_alvo": alvo["campeao_alvo"],
                "distancia": round(dist),
                "perto": 1 if dist <= RAIO_PROXIMIDADE else 0,
            })

    return linhas


def main():
    puuid = buscar_puuid("Aiolos", "GOLD")
    if not puuid:
        return

    match_ids = buscar_ids_partidas(puuid, main_module.QTD_PARTIDAS)
    todas_as_linhas = []

    for i, match_id in enumerate(match_ids):
        print(f"[{i+1}/{len(match_ids)}] Processando proximidade de {match_id}...")
        todas_as_linhas.extend(processar_partida(match_id, puuid))
        time.sleep(1.2)

    if not todas_as_linhas:
        print("\nNenhum dado coletado.")
        return

    campos = list(todas_as_linhas[0].keys())
    with open("proximidade_greggo.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(todas_as_linhas)

    print(f"\nConcluído! {len(todas_as_linhas)} linhas exportadas para proximidade_greggo.csv")


if __name__ == "__main__":
    main()
