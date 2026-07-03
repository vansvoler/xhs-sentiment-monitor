from src.collectors import scheduler


def test_start_scheduler_registers_university_news_job(monkeypatch):
    recorded_ids = []

    class _FakeScheduler:
        def add_job(self, _func, *, id, **_kwargs):
            recorded_ids.append(id)

        def start(self):
            return None

    monkeypatch.setattr(scheduler, "scheduler", _FakeScheduler())

    scheduler.start_scheduler()

    assert "collect_ucas_news" in recorded_ids
    assert "collect_university_news" in recorded_ids
