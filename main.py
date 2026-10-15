import csv
import os
import requests
import time


def carregar_env(caminho=".env"):
    """Carrega variáveis de um arquivo .env (CHAVE=valor) sem sobrescrever as já definidas."""
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), caminho)
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


carregar_env()
API_KEY = os.environ.get("RIOT_API_KEY")
if not API_KEY:
    raise SystemExit("Defina RIOT_API_KEY no arquivo .env (veja .env.example).")

REGION_ROUTING = "americas"
QUEUE_ID_RANQUEADA_SOLO = 420
QTD_PARTIDAS = 30

JOGADORES = [
    {"rotulo": "Greggo", "game_name": "Aiolos", "tag_line": "GOLD"},
]

headers = {"X-Riot-Token": API_KEY}


def buscar_puuid(game_name, tag_line):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()["puuid"]
    else:
        print(f"  Erro ao buscar PUUID de {game_name}#{tag_line}: {resp.status_code}")
        return None


def buscar_ids_partidas(puuid, count):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"start": 0, "count": count, "queue": QUEUE_ID_RANQUEADA_SOLO}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"  Erro ao buscar partidas: {resp.status_code}")
        return []


def buscar_elo(puuid):
    url = f"https://br1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        entradas = resp.json()
        for entrada in entradas:
            if entrada["queueType"] == "RANKED_SOLO_5x5":
                return f"{entrada['tier']} {entrada['rank']}"
    return "Sem elo/Unranked"


def buscar_detalhes_partida(match_id, puuid, rotulo, conta):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"  Erro ao buscar detalhes de {match_id}: {resp.status_code}")
        return None

    data = resp.json()
    participants = data["info"]["participants"]

    p = None
    for participant in participants:
        if participant["puuid"] == puuid:
            p = participant
            break

    if not p:
        return None

    # Matchup
    minha_posicao = p["teamPosition"]
    meu_time = p["teamId"]
    adversario_direto = None
    for outro in participants:
        if outro["teamPosition"] == minha_posicao and outro["teamId"] != meu_time:
            adversario_direto = outro
            break
    campeao_adversario = adversario_direto["championName"] if adversario_direto else "Desconhecido"

    return {
        "jogador": rotulo,
        "conta": conta,
        "match_id": match_id,
        "data_partida": data["info"]["gameCreation"],
        "campeao": p["championName"],
        "campeao_adversario": campeao_adversario,
        "imagem_campeao": f"https://ddragon.leagueoflegends.com/cdn/13.20.1/img/champion/{p['championName']}.png",
        "posicao": p["teamPosition"],
        "resultado": "Vitoria" if p["win"] else "Derrota",
        "duracao_min": round(data["info"]["gameDuration"] / 60, 1),
        "kills": p["kills"],
        "deaths": p["deaths"],
        "assists": p["assists"],
        "dano_total_campeoes": p["totalDamageDealtToChampions"],
        "dano_fisico_campeoes": p["physicalDamageDealtToChampions"],
        "dano_magico_campeoes": p["magicDamageDealtToChampions"],
        "dano_verdadeiro_campeoes": p["trueDamageDealtToChampions"],
        "dano_a_torres": p["damageDealtToTurrets"],
        "dano_a_objetivos": p["damageDealtToObjectives"],
        "torres_destruidas": p["turretKills"],
        "inibidores_destruidos": p["inhibitorKills"],
        "placar_visao": p["visionScore"],
        "wards_colocadas": p["wardsPlaced"],
        "wards_destruidas": p["wardsKilled"],
        "sentinelas_controle_compradas": p["visionWardsBoughtInGame"],
        "ouro_recebido": p["goldEarned"],
        "ouro_gasto": p["goldSpent"],
        "cs_lane": p["totalMinionsKilled"],
        "cs_selva": p["neutralMinionsKilled"],
        "cs_total": p["totalMinionsKilled"] + p["neutralMinionsKilled"],
    }


def main():
    todas_as_linhas = []

    for jogador in JOGADORES:
        rotulo = jogador["rotulo"]
        game_name = jogador["game_name"]
        tag_line = jogador["tag_line"]
        conta = f"{game_name}#{tag_line}"

        print(f"\nProcessando {rotulo} ({conta})...")

        puuid = buscar_puuid(game_name, tag_line)
        if not puuid:
            continue

        match_ids = buscar_ids_partidas(puuid, QTD_PARTIDAS)
        print(f"  {len(match_ids)} partidas de ranqueada solo/duo encontradas.")

        for i, match_id in enumerate(match_ids):
            print(f"  Buscando partida {i+1}/{len(match_ids)}: {match_id}")
            linha = buscar_detalhes_partida(match_id, puuid, rotulo, conta)
            if linha:
                todas_as_linhas.append(linha)
            time.sleep(1.2)

    if not todas_as_linhas:
        print("\nNenhum dado foi coletado. Verifique os erros acima.")
        return

    campos = list(todas_as_linhas[0].keys())
    with open("dados_greggo.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(todas_as_linhas)

    print(f"\nConcluído! {len(todas_as_linhas)} partidas exportadas para dados_greggo.csv")


if __name__ == "__main__":
    main()