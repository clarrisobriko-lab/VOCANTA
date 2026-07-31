from core.database import Database


def main() -> int:
    database = Database()
    try:
        repaired = database.repair_history()
        print(f"History records repaired: {repaired}")
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
