import tempfile
import unittest
from pathlib import Path

from zhenzhi_core import (
    authenticate,
    checkin,
    create_user,
    get_user_by_id,
    init_db,
    review_student_verification,
    submit_student_verification,
)


class ZhenZhiCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.db"
        init_db(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_and_authenticate_user(self):
        self.assertTrue(create_user("alice", "pw", self.db))
        user = authenticate("alice", "pw", self.db)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "alice")

    def test_daily_checkin_only_once(self):
        create_user("alice", "pw", self.db)
        user = authenticate("alice", "pw", self.db)
        ok_first, _ = checkin(user.id, self.db, reward=3)
        ok_second, _ = checkin(user.id, self.db, reward=3)
        self.assertTrue(ok_first)
        self.assertFalse(ok_second)

    def test_student_verification_approval_grants_long_quota(self):
        create_user("alice", "pw", self.db)
        user = authenticate("alice", "pw", self.db)
        submit_student_verification(user.id, "20260001", "student card", self.db)
        review_student_verification(user.id, approved=True, db_path=self.db, free_years=3, bonus_quota=999)
        refreshed = get_user_by_id(user.id, self.db)
        self.assertEqual(refreshed.student_verified, 1)
        self.assertGreaterEqual(refreshed.quota, 999)
        self.assertIsNotNone(refreshed.free_until)


if __name__ == "__main__":
    unittest.main()
