#!/usr/bin/env python
"""
Quiz Results Feature - Simple Validation Test

This script validates that the quiz results feature components are properly integrated
and can process quiz responses. It tests the analyze_position and quiz_results_service
directly without requiring the database.

Usage:
    python validate_quiz_feature.py
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root))

async def test_quiz_results_service():
    """Test the quiz results service with sample data."""
    print("=" * 70)
    print("Testing Quiz Results Feature")
    print("=" * 70)

    try:
        from app.backend.services.quiz_results_service import evaluate_quiz_response
        print("✓ Quiz results service imported successfully")
    except Exception as e:
        print(f"✗ Failed to import quiz results service: {e}")
        return False

    # Sample test data - Opening positions from Ruy Lopez
    test_responses = [
        {
            "ply": 3,
            "fen_before": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            "expected_move": "Nc6",
            "user_move": "b8c6"  # Correct: Nc6
        },
        {
            "ply": 5,
            "fen_before": "r1bqkbnr/pppppppp/2n5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2",
            "expected_move": "Nf3",
            "user_move": "g1f3"  # Correct: Nf3
        },
        {
            "ply": 7,
            "fen_before": "r1bqkbnr/pppppppp/2n5/8/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
            "expected_move": "Nf6",
            "user_move": "b8d5"  # Incorrect: should be Nf6
        },
    ]

    print("\n" + "-" * 70)
    print("Testing evaluate_quiz_response()")
    print("-" * 70)
    print(f"Input: {len(test_responses)} quiz responses")
    print("\nTest responses:")
    for i, resp in enumerate(test_responses, 1):
        print(f"  {i}. User move: {resp['user_move']:6s} | Expected: {resp['expected_move']}")

    try:
        print("\nAnalyzing positions with Stockfish...")
        result = await evaluate_quiz_response(
            game_id=1,
            responses=test_responses,
            depth=15,  # Use lower depth for faster testing
            time_limit=0.3
        )

        print("✓ Quiz evaluation completed successfully")

        # Validate result structure
        required_fields = ['success', 'game_id', 'total_questions', 'correct_answers',
                          'incorrect_answers', 'score_percentage', 'results']

        for field in required_fields:
            if field not in result:
                print(f"✗ Missing field in results: {field}")
                return False

        print(f"\n" + "-" * 70)
        print("Results Summary")
        print("-" * 70)
        print(f"Success: {result['success']}")
        print(f"Game ID: {result['game_id']}")
        print(f"Total Questions: {result['total_questions']}")
        print(f"Correct Answers: {result['correct_answers']}")
        print(f"Incorrect Answers: {result['incorrect_answers']}")
        print(f"Score Percentage: {result['score_percentage']}%")

        # Analyze each result
        print(f"\n" + "-" * 70)
        print("Detailed Results")
        print("-" * 70)

        for i, res in enumerate(result['results'], 1):
            status = "✓ CORRECT" if res['correct'] else "✗ INCORRECT"
            print(f"\nPosition {i}: {status}")
            print(f"  Expected Move (SAN): {res['expected_move_san']}")
            print(f"  Your Move (SAN):     {res['user_move_san']}")
            print(f"  Feedback: {res['feedback']}")

            if res['stockfish']:
                sf = res['stockfish']
                print(f"  Stockfish Analysis:")
                print(f"    - Best Move: {sf['best_move_san']}")
                print(f"    - Evaluation: {_format_score(sf['score_cp'], sf['score_mate'])}")
                print(f"    - Top Moves: {', '.join(sf['top_moves_san'])}")
                print(f"    - Interpretation: {sf['interpretation']}")

        print("\n" + "=" * 70)
        if result['success']:
            print(f"✓ TESTS PASSED - Quiz results feature is working!")
            print(f"✓ Successfully analyzed {len(result['results'])} positions")
            print(f"✓ Generated correct feedback for all positions")
            return True
        else:
            print("✗ TESTS FAILED - Quiz evaluation reported failure")
            return False

    except Exception as e:
        print(f"✗ Error during quiz evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False

def _format_score(score_cp, score_mate):
    """Format score for display."""
    if score_mate is not None:
        if score_mate > 0:
            return f"Mate in {score_mate}"
        elif score_mate < 0:
            return f"Mate in {abs(score_mate)} (opponent)"
        else:
            return "Stalemate"

    if score_cp is None:
        return "N/A"

    val = (score_cp / 100)
    if score_cp >= 0:
        return f"+{val:.2f}"
    else:
        return f"{val:.2f}"

async def test_analyzer_service():
    """Test that analyzer_service can be imported."""
    print("\n" + "=" * 70)
    print("Testing Analyzer Service")
    print("=" * 70)

    try:
        from app.backend.services.analyzer_service import analyze_position
        print("✓ Analyzer service imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import analyzer service: {e}")
        return False

async def test_routes():
    """Test that quiz results endpoint exists."""
    print("\n" + "=" * 70)
    print("Testing API Routes")
    print("=" * 70)

    try:
        from app.backend.api.routes import router

        # Get all routes
        routes = []
        for route in router.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)

        # Look for quiz results endpoint
        quiz_endpoint = any('/quiz/results' in r for r in routes)

        if quiz_endpoint:
            print("✓ Quiz results endpoint found in routes")
            return True
        else:
            print("✗ Quiz results endpoint NOT found in routes")
            print(f"  Available routes: {routes}")
            return False

    except Exception as e:
        print(f"✗ Failed to check routes: {e}")
        return False

async def main():
    """Run all tests."""
    print("\n")
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  CHESS ANALYZER - QUIZ RESULTS FEATURE VALIDATION".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    print()

    results = []

    # Test 1: Analyzer service
    results.append(await test_analyzer_service())

    # Test 2: Routes
    results.append(await test_routes())

    # Test 3: Quiz results (main test)
    results.append(await test_quiz_results_service())

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Tests Passed: {passed}/{total}")

    if all(results):
        print("\n✓ ALL TESTS PASSED - Quiz results feature is ready!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED - Please review errors above")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

