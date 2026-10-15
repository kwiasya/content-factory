"""Store safety: no implicit create at the default path, busy timeout, journal mode, CLI-only migrations,
read-first seeding, backups and the db command group. No network."""

import contextlib
import hashlib
import io
import json
import os
import socket
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from cf.research import backup, cli, taxonomy
from cf.research import store as st

VARS = ("CF_LOCAL_ROOT", "CF_SHARED_ROOT", "CF_FOOTAGE_ROOT", "CF_FACTORY_DB")


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        env = mock.patch.dict(os.environ, {})
        env.start()
        self.addCleanup(env.stop)
        for var in VARS:
            os.environ.pop(var, None)


class OpenTest(Base):
    def test_the_default_path_is_never_created(self):
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "shared")
        (self.dir / "shared").mkdir()
        with self.assertRaises(st.StoreMissing) as cm:
            st.open_store()
        self.assertIn("db init", str(cm.exception))
        self.assertEqual(list((self.dir / "shared").iterdir()), [])

    def test_an_unmounted_shared_root_gives_the_mount_hint_and_creates_nothing(self):
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "Volumes" / "Shared" / "content-factory")
        with self.assertRaises(st.StoreMissing) as cm:
            st.open_store()
        self.assertIn("smb://", str(cm.exception))
        self.assertFalse((self.dir / "Volumes").exists())

    def test_an_explicit_path_is_not_created_unless_create_is_true(self):
        for kw in ({}, {"create": False}):
            with self.assertRaises(st.StoreMissing) as cm:
                st.open_store(self.dir / "f.db", **kw)
            self.assertIn("db init", str(cm.exception))
        self.assertFalse((self.dir / "f.db").exists())
        with self.assertRaises(st.StoreMissing):
            st.open_store(self.dir / "a" / "f.db")
        self.assertFalse((self.dir / "a").exists())
        with st.open_store(self.dir / "a" / "f.db", create=True) as s:
            self.assertEqual(s.schema_version(), st.SCHEMA_VERSION)

    def test_create_true_refuses_a_dangling_symlink_on_the_way(self):
        link = self.dir / "content-factory"
        link.symlink_to(self.dir / "Volumes" / "Shared" / "content-factory")
        with self.assertRaises(st.StoreMissing) as cm:
            st.open_store(link / "factory.db", create=True)
        self.assertIn("smb://", str(cm.exception))
        self.assertFalse((self.dir / "Volumes").exists())

    def test_cli_with_a_missing_db_path_creates_nothing(self):
        for argv in (["watchlist", "list"], ["notes", "list"]):
            code, _, err = run([*argv, "--db", str(self.dir / "f.db")])
            self.assertEqual(code, 1)
            self.assertIn("db init", err)
        from cf.library import cli as library_cli
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(library_cli.main(["pack", "list", "--db", str(self.dir / "f.db")]), 1)
        self.assertIn("db init", err.getvalue())
        self.assertFalse((self.dir / "f.db").exists())

    def test_create_true_creates_the_default_path(self):
        os.environ["CF_FACTORY_DB"] = str(self.dir / "x" / "factory.db")
        with st.open_store(create=True) as s:
            self.assertEqual(s.path, self.dir / "x" / "factory.db")
        self.assertTrue((self.dir / "x" / "factory.db").is_file())

    def test_every_connection_waits_for_the_lock(self):
        with st.open_store(self.dir / "f.db", create=True) as s:
            self.assertGreaterEqual(s.conn.execute("PRAGMA busy_timeout").fetchone()[0], 10000)
        conn = st.connect(self.dir / "f.db", readonly=True)
        self.addCleanup(conn.close)
        self.assertGreaterEqual(conn.execute("PRAGMA busy_timeout").fetchone()[0], 10000)

    def test_a_wal_store_is_refused(self):
        st.open_store(self.dir / "f.db", create=True).close()
        conn = sqlite3.connect(self.dir / "f.db")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.close()
        with self.assertRaises(st.StoreError) as cm:
            st.open_store(self.dir / "f.db", create=True)
        self.assertIn("WAL", str(cm.exception))

    def test_migrate_false_refuses_another_version_and_leaves_it(self):
        sqlite3.connect(self.dir / "f.db").close()
        with self.assertRaises(st.SchemaMismatch) as cm:
            st.open_store(self.dir / "f.db", migrate=False, create=True)
        self.assertEqual(cm.exception.version, 0)
        with sqlite3.connect(self.dir / "f.db") as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)

    def test_a_migration_backs_the_store_up_first(self):
        path = self.dir / "f.db"
        conn = sqlite3.connect(path)
        for v, script in enumerate(st.MIGRATIONS[:5]):
            conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
        conn.close()
        st.open_store(path, seed=False, create=True).close()
        files = [p.name for p in (self.dir / "backups").iterdir()]
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith(f"-pre-v{st.SCHEMA_VERSION}.db"))
        with sqlite3.connect(self.dir / "backups" / files[0]) as old:
            self.assertEqual(old.execute("PRAGMA user_version").fetchone()[0], 5)

    def test_a_fresh_file_is_not_backed_up(self):
        st.open_store(self.dir / "f.db", create=True).close()
        self.assertFalse((self.dir / "backups").exists())

    def test_a_held_lock_during_migration_is_store_busy(self):
        path = self.dir / "f.db"
        conn = sqlite3.connect(path)
        conn.executescript(f"BEGIN;\n{st.V1}\nPRAGMA user_version = 1;\nCOMMIT;")
        conn.execute("BEGIN IMMEDIATE")
        self.addCleanup(conn.close)
        with mock.patch.object(st, "BUSY_TIMEOUT_S", 0.1), self.assertRaises(st.StoreBusy) as cm:
            st.open_store(path, seed=False, create=True)
        self.assertIn("busy", str(cm.exception))


class SeedTest(Base):
    def test_seeding_a_seeded_store_opens_no_transaction(self):
        path = self.dir / "f.db"
        st.open_store(path, create=True).close()
        with st.open_store(path, seed=False, create=True) as s:
            statements: list[str] = []
            s.conn.set_trace_callback(statements.append)
            self.assertEqual(taxonomy.load_seed(s), 0)
            self.assertFalse([x for x in statements if not x.lstrip().upper().startswith("SELECT")], statements)

    def test_watchlist_list_on_a_seeded_store_does_not_write_it(self):
        path = self.dir / "f.db"
        st.open_store(path, create=True).close()
        before = sha(path)
        self.assertEqual(run(["watchlist", "list", "--db", str(path)])[0], 0)
        self.assertEqual(sha(path), before)


class BackupTest(Base):
    def setUp(self):
        super().setUp()
        self.path = self.dir / "f.db"
        self.store = st.open_store(self.path, create=True)
        self.addCleanup(self.store.close)

    def test_name_and_label(self):
        p = backup.backup(self.store.conn, self.path, "manual", datetime(2026, 10, 15, 9, 5))
        self.assertEqual(p, self.dir.resolve() / "backups" / "factory-20261015-0905-manual.db")
        with sqlite3.connect(p) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], st.SCHEMA_VERSION)
        self.assertEqual([x.name for x in (self.dir / "backups").iterdir()], [p.name])
        with self.assertRaises(st.StoreError):
            backup.backup(self.store.conn, self.path, "Bad Label")

    def test_a_symlinked_store_backs_up_next_to_the_real_file(self):
        link = self.dir / "link" / "factory.db"
        link.parent.mkdir()
        link.symlink_to(self.path)
        self.assertEqual(backup.backups_dir(link), self.dir.resolve() / "backups")

    def test_prune_keeps_14_daily_10_bulk_and_every_other_label(self):
        for day in range(1, 21):
            backup.backup(self.store.conn, self.path, "daily", datetime(2026, 10, day, 1, 0))
            backup.backup(self.store.conn, self.path, "pre-scout", datetime(2026, 10, day, 2, 0))
            backup.backup(self.store.conn, self.path, "pre-v9", datetime(2026, 10, day, 3, 0))
            backup.backup(self.store.conn, self.path, "pre-shared", datetime(2026, 10, day, 4, 0))
        labels = [label for _, label, _ in backup.listing(self.dir / "backups")]
        self.assertEqual((labels.count("daily"), labels.count("pre-scout"), labels.count("pre-v9"),
                          labels.count("pre-shared")), (14, 10, 20, 20))
        newest = backup.newest_per_label(self.path)
        self.assertEqual(newest["daily"], "factory-20261020-0100-daily.db")

    def test_the_part_file_is_per_process_and_stale_parts_are_pruned(self):
        names = []
        real = sqlite3.connect

        def spy(target, *a, **kw):
            names.append(Path(target).name)
            return real(target, *a, **kw)
        with mock.patch.object(backup.sqlite3, "connect", spy):
            p = backup.backup(self.store.conn, self.path, "manual", datetime(2026, 10, 15, 9, 5))
        self.assertEqual(names, [f".{p.name}.{socket.gethostname()}-{os.getpid()}.part"])
        folder = p.parent
        old = folder / ".factory-20261001-0000-daily.db.other-1.part"
        fresh = folder / ".factory-20261015-0905-manual.db.other-2.part"
        for f in (old, fresh):
            f.write_bytes(b"x")
        os.utime(old, (0, 0))
        backup.prune(folder)
        self.assertEqual((old.exists(), fresh.exists(), p.exists()), (False, True, True))

    def test_ensure_daily_once_per_day(self):
        self.assertIsNotNone(backup.ensure_daily(self.store, datetime(2026, 10, 15, 8, 0)))
        self.assertIsNone(backup.ensure_daily(self.store, datetime(2026, 10, 15, 20, 0)))
        self.assertIsNotNone(backup.ensure_daily(self.store, datetime(2026, 10, 16, 8, 0)))

    def test_ensure_daily_refuses_a_store_failing_quick_check_and_writes_nothing(self):
        with mock.patch.object(backup, "quick_check", return_value="*** in database main ***\nPage 3 is never used"):
            with self.assertRaises(st.StoreError) as cm:
                backup.ensure_daily(self.store)
        self.assertIn("quick_check", str(cm.exception))
        self.assertFalse((self.dir / "backups").exists())


class DbCommandsTest(Base):
    def test_init_creates_at_the_default_path_and_other_commands_do_not(self):
        os.environ["CF_SHARED_ROOT"] = str(self.dir)
        code, _, err = run(["watchlist", "list"])
        self.assertEqual(code, 1)
        self.assertIn("db init", err)
        self.assertFalse((self.dir / "factory.db").exists())
        code, out, _ = run(["db", "init", "--json"])
        self.assertEqual((code, json.loads(out)["created"]), (0, True))
        self.assertEqual(run(["watchlist", "list"])[0], 0)
        self.assertEqual(json.loads(run(["db", "init", "--json"])[1])["created"], False)

    def test_check_reports_a_healthy_store_and_fails_on_problems(self):
        os.environ["CF_SHARED_ROOT"] = str(self.dir)
        path = self.dir / "factory.db"
        code, out, _ = run(["db", "check", "--json"])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out)["exists"])
        st.open_store(path, create=True).close()
        before = sha(path)
        code, out, _ = run(["db", "check", "--json"])
        data = json.loads(out)
        self.assertEqual(code, 0, data)
        self.assertEqual((data["version"], data["journal_mode"], data["quick_check"], data["shared_root_available"]),
                         (st.SCHEMA_VERSION, "delete", "ok", True))
        self.assertEqual(sha(path), before)
        self.assertFalse((self.dir / "backups").exists())
        with sqlite3.connect(path) as conn:
            conn.execute("PRAGMA user_version = 3")
        self.assertEqual(run(["db", "check"])[0], 1)

    def test_check_names_the_unmounted_shared_root(self):
        os.environ["CF_SHARED_ROOT"] = str(self.dir / "gone")
        code, out, _ = run(["db", "check"])
        self.assertEqual(code, 1)
        self.assertIn("smb://", out)
        self.assertFalse((self.dir / "gone").exists())

    def test_backup_and_migrate(self):
        path = self.dir / "f.db"
        st.open_store(path, create=True).close()
        code, out, _ = run(["db", "backup", "--label", "pre-shared", "--db", str(path), "--json"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["backup"].endswith("-pre-shared.db"))
        code, out, _ = run(["db", "migrate", "--db", str(path), "--json"])
        self.assertEqual((code, json.loads(out)["version"]), (0, st.SCHEMA_VERSION))

    def test_the_first_command_of_the_day_takes_the_daily_backup(self):
        path = self.dir / "f.db"
        st.open_store(path, create=True).close()
        run(["watchlist", "list", "--db", str(path)])
        run(["watchlist", "list", "--db", str(path)])
        labels = [label for _, label, _ in backup.listing(self.dir / "backups")]
        self.assertEqual(labels, ["daily"])

    def test_bulk_commands_carry_their_backup_label(self):
        parser = cli.build_parser()
        for argv, label in ((["scout", "w"], "pre-scout"), (["snapshot", "w"], "pre-snapshot"),
                            (["fetch", "x"], "pre-fetch"), (["own", "sync"], "pre-own"),
                            (["watchlist", "list"], None)):
            with self.subTest(argv=argv):
                self.assertEqual(getattr(parser.parse_args(argv), "backup", None), label)


if __name__ == "__main__":
    unittest.main()
