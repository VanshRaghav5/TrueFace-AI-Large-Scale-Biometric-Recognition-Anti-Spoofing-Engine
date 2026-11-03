from backend.realtime.face_tracker import FaceTracker


def test_tracker_reuses_track_and_expires_it():
    tracker = FaceTracker(timeout_frames=2)
    first = tracker.update([[0, 0, 10, 10]], 1)[0]
    second = tracker.update([[1, 1, 11, 11]], 2)[0]

    assert second.track_id == first.track_id
    assert tracker.active_track_count == 1

    tracker.update([], 5)
    assert tracker.active_track_count == 0


def test_tracker_assigns_distinct_ids_to_non_overlapping_faces():
    tracker = FaceTracker()
    tracks = tracker.update([[0, 0, 10, 10], [50, 50, 60, 60]], 1)

    assert len({track.track_id for track in tracks}) == 2
