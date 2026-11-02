"""Memorization progress calculations."""


def calculate_progress(plans: list[dict]) -> dict:
    planned = set()
    completed = set()
    completed_plans = 0

    for plan in plans:
        surah = plan["surah_number"]
        ayahs = {
            (surah, number)
            for number in range(
                plan["start_ayah"],
                plan["end_ayah"] + 1,
            )
        }

        planned.update(ayahs)

        if plan["status"] == "completed":
            completed_plans += 1
            completed.update(ayahs)

    total = len(planned)
    done = len(completed)

    return {
        "total_plans": len(plans),
        "completed_plans": completed_plans,
        "unique_planned_ayahs": total,
        "completed_ayahs": done,
        "completion_rate": round(done / total * 100, 2) if total else 0.0,
    }
