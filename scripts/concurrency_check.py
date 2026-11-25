"""Dispara centenas de transferências ao mesmo tempo e confere se o dinheiro bate.

Uso (com a API rodando via docker compose):
    python scripts/concurrency_check.py --requests 300

O script cria duas contas, faz transferências cruzadas em paralelo (A->B e B->A)
e no fim verifica que:
  1. a soma dos saldos não mudou (nenhum centavo criado ou perdido);
  2. o saldo de cada conta bate com a soma do extrato;
  3. nenhum saldo ficou negativo.
"""

import argparse
import asyncio
import random
import uuid

import httpx


async def main(base_url: str, total_requests: int) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        ids = []
        for name in ("Conta A", "Conta B"):
            account = (await client.post("/accounts", json={"owner_name": name})).json()
            await client.post(
                f"/accounts/{account['id']}/deposits",
                json={"amount_cents": 100_000},
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
            ids.append(account["id"])

        async def one_transfer():
            origin, target = random.sample(ids, 2)
            response = await client.post(
                "/transfers",
                json={
                    "from_account_id": origin,
                    "to_account_id": target,
                    "amount_cents": random.randint(1, 5_000),
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
            return response.status_code

        statuses = await asyncio.gather(*(one_transfer() for _ in range(total_requests)))

        balances = []
        for account_id in ids:
            check = (await client.get(f"/accounts/{account_id}/reconciliation")).json()
            balances.append(check["balance_cents"])
            assert check["consistent"], f"Conta {account_id} inconsistente: {check}"
            assert check["balance_cents"] >= 0, f"Conta {account_id} ficou negativa"

        assert sum(balances) == 200_000, f"Soma mudou: {sum(balances)}"

        ok = statuses.count(201)
        refused = statuses.count(422)
        print(f"{total_requests} requisições: {ok} concluídas, {refused} recusadas por saldo")
        print(f"Saldos finais: {balances} (soma {sum(balances)})")
        print("Tudo consistente.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=200)
    args = parser.parse_args()
    asyncio.run(main(args.url, args.requests))
