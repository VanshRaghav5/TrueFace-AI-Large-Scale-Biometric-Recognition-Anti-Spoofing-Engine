from backend.realtime_demo import DEFAULT_ENROLLMENT_DIR, REPOSITORY_ROOT


def test_default_enrollment_directory_is_repository_local():
    assert DEFAULT_ENROLLMENT_DIR == REPOSITORY_ROOT / "Trueface_Dataset"
