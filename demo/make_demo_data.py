"""
make_demo_data.py
=================
Generates a fictional athlete (Jordan Taylor) for the dashboard's sample view
(index.html?sample=true): minute-by-minute HR sessions, weekly questionnaire
reports and a fully filled Individual Performance Plan.

Every full week has at least 10 hours of training. The data runs up to the
day the script is run, so re-run it to refresh the sample:

    python demo/make_demo_data.py
"""

import csv
import json
import os
import random
from datetime import date, datetime, timedelta

ATHLETE   = "Jordan Taylor"
MAX_HR    = 195
WEEKS     = 20          # weeks of history, including the current one
MIN_WEEK  = 600         # minutes — every full week trains at least 10 hours
UTC_SHIFT = 6           # sessions are planned in local time (UTC-6) and stored as UTC

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
random.seed(2027)

# Weekly template: weekday (0 = Mon) → [(local start hour, type code, minutes, intensity profile)]
WEEK_PLAN = {
    0: [(9, "G - Goalball Practice", 120, "goalball"), (14, "W - Strength", 60, "weights")],
    1: [(8, "E - Aerobic", 50, "aerobic"), (17, "M - Mobility", 30, "easy")],
    2: [(9, "G - Goalball Practice", 120, "goalball"), (14, "W - Strength", 60, "weights")],
    3: [(8, "H - Intervals", 40, "hiit"), (17, "R - Recovery", 30, "easy")],
    4: [(9, "G - Goalball Practice", 120, "goalball"), (14, "W - Strength", 60, "weights")],
    5: [(10, "E - Aerobic", 60, "aerobic")],
}

# Main-set heart rate as a fraction of max HR (low, high)
PROFILES = {
    "goalball": (0.62, 0.86),
    "weights":  (0.55, 0.78),
    "aerobic":  (0.70, 0.80),
    "hiit":     (0.72, 0.93),
    "easy":     (0.50, 0.60),
}


def session_hr(profile: str, minutes: int) -> list[int]:
    """Per-minute heart rate: 10-minute warm-up ramp, main set, 5-minute cool-down."""
    lo, hi = PROFILES[profile]
    out = []
    for m in range(minutes):
        if m < 10:
            pct = 0.50 + (lo + 0.05 - 0.50) * m / 10
        elif m >= minutes - 5:
            pct = lo
        elif profile == "hiit":
            pct = hi if (m // 3) % 2 == 0 else lo + 0.05   # 3 on / 3 off
        elif profile == "goalball":
            pct = hi if random.random() < 0.3 else random.uniform(lo, hi - 0.08)  # repeated efforts
        else:
            pct = random.uniform(lo, hi)
        out.append(round(MAX_HR * pct + random.uniform(-3, 3)))
    return out


def build_weeks(today: date):
    """Return [(monday, [(start datetime local, type, minutes, profile)])] for each week."""
    this_monday = today - timedelta(days=today.weekday())
    weeks = []
    for w in range(WEEKS - 1, -1, -1):
        monday = this_monday - timedelta(weeks=w)
        # Gentle progression with a lighter week every fourth week keeps ACWR in the optimal range
        scale = 0.92 if w % 4 == 2 else 1.0 + 0.01 * (WEEKS - w) / WEEKS
        sessions = []
        for day, plan in WEEK_PLAN.items():
            d = monday + timedelta(days=day)
            for hour, code, minutes, profile in plan:
                start = datetime(d.year, d.month, d.day, hour, random.choice([0, 0, 15, 30]))
                sessions.append((start, code, max(20, round(minutes * scale * random.uniform(0.92, 1.08))), profile))
        # Top up the longest practice if random variation dipped below the weekly minimum
        short = MIN_WEEK + 15 - sum(s[2] for s in sessions)
        if short > 0:
            i = max(range(len(sessions)), key=lambda k: sessions[k][2])
            s = sessions[i]
            sessions[i] = (s[0], s[1], s[2] + short, s[3])
        weeks.append((monday, sessions))
    return weeks


def write_hr(weeks, now: datetime, today: date):
    rows = []
    sid = 1900000000
    for _, sessions in weeks:
        for start, code, minutes, profile in sessions:
            if start + timedelta(minutes=minutes) > now:
                continue   # no future sessions
            sid += 1
            utc = start + timedelta(hours=UTC_SHIFT)
            for m, hr in enumerate(session_hr(profile, minutes)):
                ts = (utc + timedelta(minutes=m)).strftime("%Y-%m-%dT%H:%M:00Z")
                rows.append([sid, ts, hr, code, MAX_HR, ATHLETE.replace(" ", "_") + ".csv", today.isoformat()])
    with open(os.path.join(OUT_DIR, "hr_data.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["session_id", "time_stamp", "heart_rate", "session_type", "hr_peak_myzone", "file_name", "last_updated"])
        w.writerows(rows)
    return len(rows)


Q_HEADER = [
    "Timestamp", "What is the Month of the week you are reporting?",
    "Please specify the date for the Monday you are reporting. ", "Name",
    "Do you have a workout that was not captured in MyZone?", "What type of Workout?",
    "How long was your workout?", "What was your rate of perceived exertion for this session?",
    "Do you have another workout to report?", "What type of Workout?", "How long was your workout?",
    "What was your rate of perceived exertion for this session?",
    "Do you have another workout to report?", "What type of Workout?", "How long was your workout?",
    "What was your rate of perceived exertion for this session?",
    "Do you have another workout to report?",
    "Have you had any DIFFICULTIES PARTICIPATING in normal training and competition due to injury, illness or other health problems during the past week?",
    "To what extent have you modified your training or competition due to injury, illness or other health problems during the past week? ",
    "To what extent has injury, illness or other health problems affected your performance during the past week?",
    "To what extent have you experienced pain/symptoms/health complaints during the past week?",
    "Has this specific injury/illness/health problems previously been reported in this form?",
    "When did the injury/illness occur?", "During what type of training were you injured?",
    "What was the mechanism of injury/illness", "During what part of competition were you injured?",
    "What was the mechanism of injury/illness", "Please identify how you sustained this traumatic injury",
    "Please indicate the type of overuse injury.", "Type of Illness",
    "Level of Stress", "Level of Enjoyment", "Quality of Sleep", "Quality of Eating", "Time Management",
    "Overall Mood", "Level of Motivation", "Level of Confidence", "Overall Mental Health",
    "Overall Mental Performance",
    "Is there anything you would like to share with your IST and coaches to help you optimize your health and performance?",
]

FULL = "Full participation WITHOUT injury/illness/other health problems"


def score(v: int, top_label: str = "5 - High", bottom_label: str = "1 - Low") -> str:
    return top_label if v == 5 else bottom_label if v == 1 else str(v)


def write_questionnaire(weeks, now: datetime):
    rows = []
    for i, (monday, _) in enumerate(weeks):
        submitted = datetime(monday.year, monday.month, monday.day, 19, 30) + timedelta(days=6, minutes=random.randint(0, 120))
        if submitted > now:
            continue   # the current week hasn't been reported yet
        r = [""] * len(Q_HEADER)
        r[0] = f"{submitted.month}/{submitted.day}/{submitted.year} {submitted.strftime('%H:%M:%S')}"
        r[1] = monday.strftime("%B")
        r[2] = str(monday.day)
        r[3] = ATHLETE
        # Every third week: a home mobility session that MyZone didn't capture
        if i % 3 == 1:
            r[4:9] = ["Yes", "M - Stretching & Mobility", "0.5", "2", "No"]
        else:
            r[4] = "No"
        # One early week with a minor ankle niggle, managed without missing training
        if i == 5:
            r[17:23] = ["Full participation WITH injury/illness/other health problems", "To a minor extent",
                        "To a minor extent", "Mild pain/symptoms/health complaints", "No", "Training"]
            r[23], r[24] = "Sport-Specific", "Other"
        else:
            r[17] = FULL
        stress = random.choice([2, 2, 3])
        trend = min(5, 4 + (i > WEEKS - 8 and random.random() < 0.5))   # wellbeing lifts in recent weeks
        wb = [stress, trend, random.choice([3, 4, 4]), 4, random.choice([3, 4]), trend,
              random.choice([4, 5]), random.choice([3, 4, 4, 5]), trend, random.choice([4, 4, 5])]
        r[30:40] = [score(v) for v in wb]
        r[40] = "No" if i % 4 else "Feeling strong — shoulder prehab is helping on long practice days."
        rows.append(r)
    # The latest report's note shows on the athlete page
    rows[-1][40] = ("Feeling sharp after the IPP meeting. Release speed is up on video — "
                    "would like extra time with S&C on rotational power before the next block.")
    with open(os.path.join(OUT_DIR, "questionnaire.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(Q_HEADER)
        w.writerows(rows)
    return len(rows)


def write_ipp(today: date, last_week_hours: float):
    completed   = today - timedelta(days=today.weekday() + 6)   # last Tuesday
    next_review = completed + timedelta(weeks=6)
    rated = lambda names, ratings, prio: [
        {"component": n, "rating": r, "priority": "Yes" if n in prio else "No"} for n, r in zip(names, ratings)]
    plan = {
        "header": {
            "athlete": ATHLETE,
            "position": "Centre",
            "trainingBlock": "Fall Block 2 — Pre-Competition",
            "dateCompleted": completed.isoformat(),
            "nextReview": next_review.isoformat(),
        },
        "offensive": rated(
            ["Spin / Non Spin Starting Position / Set Up", "Spin Shot - Stage 1", "Spin Shot - Stage 2",
             "Spin Shot - Stage 3", "Spin Shot - Stage 4", "Non Spin - Steps", "Non Spin - Back Swing",
             "Non Spin - Release", "Spin / Non Spin Follow Through", "Accuracy"],
            [4, 4, 3, 3, 2, 4, 4, 3, 3, 3],
            {"Spin Shot - Stage 4", "Accuracy"}),
        "defensive": rated(
            ["Ready position", "Alignment", "First movement / reaction", "Body Position", "Extension / length",
             "Hand / arm position", "Leg Position", "Range", "Hold Position / Rollng forward / backwards",
             "Ball control"],
            [5, 4, 3, 4, 4, 4, 3, 3, 4, 4],
            {"First movement / reaction"}),
        "priorities": [
            ["Release speed on the spin shot (Stage 4)",
             "Target: average release speed of 55 km/h on video by the Nov review"],
            ["Shot accuracy to the corners",
             "Target: 7/10 on the corner-target drill, tracked weekly in practice"],
            ["First movement on cross-court throws",
             "Target: reaction time under 0.45 s on the defensive reaction drill"],
        ],
        "reflection": (
            "Improved: my ready position and ball control are much more consistent, and I've hit every "
            "practice since August. My non-spin release is quicker.\n\n"
            "Needs improvement: I lose speed at Stage 4 of the spin shot when I'm tired late in practice, "
            "and my first step on cross-court balls is still a beat late."),
        "checkin": {
            "actualHrs": round(last_week_hours, 1),
            "targetHrs": 10,
            "hoursStatus": "Target met",
            "loadStatus": "On target",
            "acwrValue": 1.04,
            "acwrStatus": "Optimal",
            "participation": "Full",
            "wellbeing": "Improving",
        },
        "dashboardReflection": (
            "Yes. I'm averaging over 11 hours a week with steady load (ACWR around 1.0), so I can add "
            "shooting volume safely. Three of my weights sessions each week support release speed, and the "
            "Thursday interval session matches the repeated efforts I need on defence. My sleep score dips "
            "on double days — I'll protect bedtime on Mondays and Wednesdays."),
        "nextAction": (
            "Film 20 spin shots after Wednesday practice each week and log release speed; "
            "share the clip with coach before Friday's session."),
        "coachFeedback": (
            "Great consistency this block — training volume and attendance are exactly where they need to be. "
            "Keep the extra shooting volume to 20 reps so quality stays high, and bring the same intent to "
            "the reaction drill as you do to shooting."),
        "ist": [
            {"discipline": "ATHLETIC THERAPY\nAlice Sobiesiak", "items": [
                {"focus": "Shoulder health under higher throwing volume",
                 "actions": "Prehab circuit 3× per week before practice; monthly screen",
                 "measure": "Pain-free throwing; ROM within 5° side to side",
                 "links": "DTE 1", "status": "On track"},
                {"focus": "Left ankle stability",
                 "actions": "Balance and landing progressions in warm-up",
                 "measure": "Y-balance score within 4% side to side",
                 "links": "DTE 3", "status": "In progress"},
            ]},
            {"discipline": "STRENGTH & CONDITIONING\nJustin Staffiere", "items": [
                {"focus": "Rotational power for release speed",
                 "actions": "Med-ball rotational throws and trap-bar jumps, 3× per week",
                 "measure": "Med-ball throw +10% by the Nov review",
                 "links": "DTE 1", "status": "On track"},
                {"focus": "Repeat-effort capacity on defence",
                 "actions": "Thursday interval session; 3-on / 3-off format",
                 "measure": "HR recovery under 60 s between efforts",
                 "links": "DTE 3", "status": "In progress"},
            ]},
            {"discipline": "MENTAL PERFORMANCE\nChloe Gagnon", "items": [
                {"focus": "Pre-throw routine under pressure",
                 "actions": "Same 3-step routine on every throw in practice and games",
                 "measure": "Routine used on 9/10 throws (coach tally)",
                 "links": "DTE 2", "status": "On track"},
                {"focus": "Sleep on double-session days",
                 "actions": "Wind-down plan; lights out by 22:30 on Mon/Wed",
                 "measure": "Sleep score ≥ 4 on weekly check-in",
                 "links": "All", "status": "In progress"},
            ]},
        ],
        "istNotes": (
            "S&C and AT share one throwing-volume plan so shoulder load and power work don't peak in the "
            "same week. MP routine is rehearsed in Wednesday shooting so it carries into the corner-target drill."),
        "commitment": {
            "athlete": ATHLETE,
            "coach": "Head Coach",
            "date": completed.isoformat(),
            "nextReview": next_review.isoformat(),
        },
    }
    data = {"athletes": [{"sheet": ATHLETE.split()[0], "hasContent": True, "plan": plan}]}
    with open(os.path.join(OUT_DIR, "ipp_data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def main():
    now = datetime.now()
    today = now.date()
    weeks = build_weeks(today)
    n_hr = write_hr(weeks, now, today)
    n_q = write_questionnaire(weeks, now)
    last_week = sum(s[2] for s in weeks[-2][1]) / 60
    write_ipp(today, last_week)
    full = [sum(s[2] for s in ss) / 60 for _, ss in weeks[:-1]]
    print(f"{n_hr:,} HR rows, {n_q} questionnaire reports")
    print(f"Weekly hours (full weeks): min {min(full):.1f}, avg {sum(full) / len(full):.1f}, last week {last_week:.1f}")


if __name__ == "__main__":
    main()
