#!/usr/bin/env python3
"""
Comprehensive evaluation of pipeline across all 6 sample meetings.
Generates metrics, precision, recall, F1, and comparison with gold standard.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline.pipeline import run_pipeline

# Expected gold standard for each meeting
# Format: {meeting_num: {sentence_text: expected_is_decision}}
GOLD_STANDARDS = {
    1: {
        "I will handle the API refactor by Friday.": True,
        "Charlie, can you write the integration tests for the new endpoints?": True,
        "I will write the tests by Wednesday.": True,
        "please update the project documentation with the new API specs.": True,
        "I'll update the docs by Thursday.": True,
        "Let's also follow up on the deployment pipeline issue from last week.": True,
        "I'll look into the CI/CD pipeline and fix the failing builds.": True,
        "Let's meet again on Friday to review progress.": False,  # Just scheduling, not an action
        "Good morning everyone.": False,
        "Sure.": False,
        "Great.": False,
        "Yes,": False,
        "Perfect.": False,
        "Sounds good.": False,
    },
    2: {
        "I need to benchmark the throughput by next Tuesday.": True,
        "I should also update the architecture diagram to reflect the changes.": True,
        "Can you also check if we need to upgrade the load balancer?": True,
        "I will check the load balancer compatibility by Monday.": True,
        "I'll reach out to the DevOps lead tomorrow.": True,
        "Let's schedule a follow-up meeting after the benchmarks are done.": False,
        "Agreed.": False,
        "Good point.": False,
    },
    3: {
        "I need to optimize the database queries by next Wednesday.": True,
        "Mike, can you also profile the API response times?": True,
        "I'll have the mockups ready by Friday.": True,
        "I'll integrate Sentry before the next release.": True,
        "I'll write the migration script this week.": True,
        "I will document the rollback steps.": True,
        "I will schedule a go/no-go meeting for next Thursday to review everything.": True,
        "jen, can you draft the help articles by next Monday?": True,
        "Let me set up the load testing environment.": True,
        "jen, please coordinate with Tom on the error states for each step.": True,
    },
    4: {
        "I will increase the connection pool limit from 50 to 200 and add connection timeout monitoring.": True,
        "I'll configure CloudWatch alarms by end of day.": True,
        "Can you also add a dashboard panel for real-time connection metrics?": True,
        "Yes, I'll create the Grafana dashboard this afternoon.": True,
        "Engineer1, can you document the troubleshooting steps?": True,
        "Sure, I'll update the runbook by tomorrow morning.": True,
        "I'll redesign the load test suite to include connection pool stress scenarios.": True,
        "I'll implement the circuit breaker pattern using Resilience4j by end of next week.": True,
        "I'll audit all database connections across microservices.": True,
        "I'll draft the postmortem report for the status page.": True,
        "Let's schedule a follow-up review for next Wednesday to check progress on all these items.": False,
    },
    5: {
        "I'll finish the OAuth integration by tomorrow.": True,
        "I will reach out to DevOps today and get you those keys.": True,
        "I'll prepare a technical comparison document by end of day.": True,
        "I'll send you the bug reports after this meeting.": True,
        "I'll fix those bugs before moving to notifications.": True,
        "I need everyone to review the component library.": True,
        "I'll share the API documentation by Wednesday.": True,
        "I need to prepare the demo environment.": True,
        "I'll have the updated prototype ready by Saturday.": True,
        "I finished the search feature yesterday.": False,
        "Today I'm going to start on the notification system.": False,
        "I've been testing the search feature.": False,
        "Let's meet again tomorrow same time.": False,
    },
    6: {
        "We should look into that.": True,
        "Let's keep monitoring the situation.": True,
        "Let's maybe revisit the churn issue next quarter.": True,
        # Everything else in meeting 6 is observation/metric/reaction
        "So the quarterly numbers look pretty good overall.": False,
        "Revenue is up 12% compared to last quarter.": False,
        "Yeah, the marketing campaign really helped drive new signups.": False,
        "The conversion rate from trial to paid went from 15% to 22%.": False,
        "That's great.": False,
        "The board will be happy with these numbers.": False,
        "We do have some churn in the enterprise segment though.": False,
        "We lost two large accounts last month.": False,
        "Apparently they switched to a competitor with better integrations.": False,
        "That's concerning.": False,
        "The product team is already working on more integrations.": False,
        "They mentioned something about a Salesforce connector.": False,
        "I think the real issue is response time from our support team.": False,
        "Both accounts complained about slow support.": False,
        "Hmm, that's a valid point.": False,
        "Agreed.": False,
        "Anyway, the new pricing tier seems to be working well.": False,
        "Yes, the mid-tier plan is the most popular choice now.": False,
        "Good.": False,
        "Anything else to discuss?": False,
        "I think that covers it for today.": False,
        "Sounds good.": False,
        "Have a good rest of the week.": False,
    }
}


def normalize_text(text):
    """Normalize text for comparison."""
    return text.lower().strip()


def calculate_metrics(meeting_num, extracted_tasks, gold_standard):
    """
    Calculate precision, recall, F1 for a meeting.
    
    Args:
        meeting_num: Meeting number (1-6)
        extracted_tasks: List of task dicts from pipeline
        gold_standard: Dict mapping sentence -> expected_is_decision
    
    Returns:
        Dict with metrics
    """
    # Collect extracted sentence texts
    extracted_texts = set()
    for task in extracted_tasks:
        text = task.get("evidence", {}).get("text", "").lower().strip()
        if text:
            extracted_texts.add(text)
    
    # Collect gold standard true positives (sentences that SHOULD be tasks)
    gold_true_positives = set()
    for text, is_decision in gold_standard.items():
        if is_decision:
            gold_true_positives.add(normalize_text(text))
    
    # Calculate metrics
    tp = len(extracted_texts & gold_true_positives)  # Correct extractions
    fp = len(extracted_texts - gold_true_positives)  # False positives
    fn = len(gold_true_positives - extracted_texts)  # False negatives
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "meeting": meeting_num,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "extracted_count": len(extracted_texts),
        "gold_count": len(gold_true_positives),
        "extracted_tasks": extracted_tasks,
    }


def main():
    print("=" * 80)
    print("PIPELINE EVALUATION: All 6 Sample Meetings")
    print("=" * 80)
    
    all_metrics = []
    total_tp = total_fp = total_fn = 0
    
    for meeting_num in range(1, 7):
        print(f"\n{'=' * 80}")
        print(f"MEETING {meeting_num}: sample_meeting_{meeting_num}.txt")
        print("=" * 80)
        
        # Read transcript
        transcript_file = f"transcripts/sample_meeting_{meeting_num}.txt"
        try:
            with open(transcript_file, 'r') as f:
                transcript = f.read()
        except FileNotFoundError:
            print(f"[!] File not found: {transcript_file}")
            continue
        
        # Run pipeline
        try:
            print(f"[*] Running pipeline...")
            tasks = run_pipeline(transcript)
            print(f"[+] Pipeline completed")
        except Exception as e:
            print(f"[!] Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # Calculate metrics
        gold = GOLD_STANDARDS.get(meeting_num, {})
        metrics = calculate_metrics(meeting_num, tasks, gold)
        
        # Accumulate totals
        total_tp += metrics["tp"]
        total_fp += metrics["fp"]
        total_fn += metrics["fn"]
        
        all_metrics.append(metrics)
        
        # Print meeting results
        print(f"\n[RESULTS]")
        print(f"  Extracted tasks: {metrics['extracted_count']}")
        print(f"  Gold standard tasks: {metrics['gold_count']}")
        print(f"  True Positives: {metrics['tp']}")
        print(f"  False Positives: {metrics['fp']}")
        print(f"  False Negatives: {metrics['fn']}")
        print(f"  Precision: {metrics['precision']:.3f} ({metrics['tp']}/{metrics['tp'] + metrics['fp']})")
        print(f"  Recall: {metrics['recall']:.3f} ({metrics['tp']}/{metrics['tp'] + metrics['fn']})")
        print(f"  F1 Score: {metrics['f1']:.3f}")
        
        if tasks:
            print(f"\n[EXTRACTED TASKS]")
            for i, task in enumerate(tasks, 1):
                confidence = task.get("confidence", 0)
                assignee = task.get("assignee", "Unknown")
                print(f"  {i}. [{confidence:.2f}] {task.get('task', 'N/A')}")
                print(f"     → Assignee: {assignee}")
    
    # Print aggregate results
    print(f"\n\n{'=' * 80}")
    print("AGGREGATE METRICS (All 6 Meetings)")
    print("=" * 80)
    
    total_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    total_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    total_f1 = 2 * (total_precision * total_recall) / (total_precision + total_recall) if (total_precision + total_recall) > 0 else 0
    
    print(f"\nOverall Statistics:")
    print(f"  Total True Positives: {total_tp}")
    print(f"  Total False Positives: {total_fp}")
    print(f"  Total False Negatives: {total_fn}")
    print(f"  -" * 40)
    print(f"  Overall Precision: {total_precision:.3f}")
    print(f"  Overall Recall: {total_recall:.3f}")
    print(f"  Overall F1 Score: {total_f1:.3f}")
    
    # Per-meeting summary
    print(f"\n\nPer-Meeting Summary:")
    print(f"{'Meeting':<10} {'Tasks':<10} {'TP':<6} {'FP':<6} {'FN':<6} {'Precision':<12} {'Recall':<12} {'F1':<10}")
    print("-" * 80)
    for m in all_metrics:
        print(f"Meeting {m['meeting']:<2} {m['extracted_count']:<10} {m['tp']:<6} {m['fp']:<6} {m['fn']:<6} "
              f"{m['precision']:.3f}       {m['recall']:.3f}       {m['f1']:.3f}")
    
    # Expected vs actual for meeting 6 (status meeting)
    print(f"\n\n{'=' * 80}")
    print("MEETING 6 DETAILED ANALYSIS (Expected vs Actual)")
    print("=" * 80)
    m6_metrics = next((m for m in all_metrics if m['meeting'] == 6), None)
    if m6_metrics:
        print(f"Expected outcome after fixes:")
        print(f"  - Input: 16 status/metric/reaction sentences + 3 action items")
        print(f"  - Output: ~3-4 tasks (only the 3 action items)")
        print(f"  - Precision target: ~80%")
        print(f"  - Recall target: 100%")
        print(f"\nActual results:")
        print(f"  - Tasks extracted: {m6_metrics['extracted_count']}")
        print(f"  - True Positives: {m6_metrics['tp']}")
        print(f"  - False Positives: {m6_metrics['fp']}")
        print(f"  - Precision: {m6_metrics['precision']:.1%}")
        print(f"  - Recall: {m6_metrics['recall']:.1%}")
        print(f"  - F1: {m6_metrics['f1']:.3f}")
        if m6_metrics['extracted_count'] <= 4 and m6_metrics['precision'] >= 0.75:
            print(f"\n[✓] MEETING 6 PASSED: Acceptable precision and reduced false positives")
        else:
            print(f"\n[!] MEETING 6: May need further tuning")


if __name__ == "__main__":
    main()
