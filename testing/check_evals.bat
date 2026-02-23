@echo off
REM Check evals table directly with psql

echo ======================================================================
echo CHECKING EVALS TABLE
echo ======================================================================
echo.

psql -U postgres -d chess_analyzer -c "SELECT COUNT(*) as evals_count FROM evals;"

echo.
echo Showing first 5 evaluations:
echo ======================================================================

psql -U postgres -d chess_analyzer -c "SELECT fen, best_move, score_cp, depth FROM evals LIMIT 5;"

echo.
echo Done.

