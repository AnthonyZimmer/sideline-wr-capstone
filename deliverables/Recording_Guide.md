# Sideline recording guide

Draft speaking notes. Review and use your own voice. These are presentation notes, not student-authored AI prompts. Confirm the required recording duration. Aim for roughly 8–10 minutes including the live walkthrough if appropriate. Keep your face visible throughout.

## Slide 1: Sideline

Introduce Sideline as a system for comparing two wide receivers. Explain that the project focuses on full PPR and helps fantasy users see deeper statistics in one place. The prototype runs locally and uses real nflverse data.

## Slide 2: The problem and my contribution

Explain your original motivation in your own words. Describe how a typical lineup choice sends a user across multiple pages to find playing time, targets and opponent strength. The innovation is the combined comparison experience. Avoid claiming that collecting these statistics alone creates a uniquely superior prediction model.

## Slide 3: Project scope

Explain the decision to restrict the project to wide receivers. That reduces inconsistent scoring patterns across positions and leaves time to build and evaluate a complete system. SQL supports the data layer and Python supports modeling and Flask. Mention that the project currently runs on a local computer.

## Slide 4: Receiver selection

Demonstrate the selection screen live if possible. Select Adams and Golden for 2026 Week 1. Explain that historical comparison weeks require the same prediction cutoff as a forecast. Show that the interface accepts two distinct players and includes team context when available. Allow about 45 seconds for this demonstration.

## Slide 5: Projected PPR and recommendation

Walk through the two projected totals. Explain that the recommendation comes from the forecast gap, while the displayed range is illustrative and comes from validation residuals. It is not a calibrated individual-player confidence interval. Save the actual outcomes for the findings section. Source: results/enhanced/verified_week1.json.

## Slide 6: Opportunity and matchup evidence

Show the statistics table and explain target share as the receiver share of team targets. Describe snap share as playing time, which differs from routes run. Explain the red-zone denominator and that defensive context comes from previous games. The highlighted statistics are descriptive comparisons, not proof of how the model reached its prediction.

## Slide 7: Methodology and missing inputs

Open the methodology area and point to the limits. The source audit found snap coverage around 96 percent and drop coverage around 77 percent. Training medians handle missing model inputs. Explain why using historical game-day weather would leak information into a pregame prediction and why the current model excludes it.

## Slide 8: Input validation

Demonstrate the same-player error and correct it. Explain that a model requires at least three historical appearances before returning a forecast. The automated checks cover API validation and cutoff behavior. A future user study will determine whether people understand these messages and the comparisons.

## Slide 9: Projection methodology

Explain the three-game and eight-game windows and the recent usage trends. The model predicts targets, catches, yards, touchdowns and other scoring, then calculates PPR. There is no arbitrary hot-streak boost. Training includes 5,168 appearances. Fourteen automated checks pass, including a check that changing current and future outcomes does not change features.

## Slide 10: More statistics do not guarantee lower error

Define mean absolute error as average distance between predicted and actual points. Lower is better. The enhanced model does not beat the eight-game active-appearance average on 2025 MAE, but its RMSE is lower. The 2026 improvement is small. Explain that 2026 outcomes were previously inspected, so this is not an untouched test. Source: results/enhanced/evaluation.json.

## Slide 11: My roster: the Week 1 comparison

Explain that the five Week 1 league scores match the source data. Although average error improves against the original recorded-game baseline, the Adams versus Golden recommendation is wrong. Discuss why single-week outcomes remain uncertain. The larger evaluation uses an active-appearance baseline, so identify the baseline difference. Weeks 2 through 4 still need league confirmation.

## Slide 12: Reflection and future work

Adapt this reflection to your own experience before recording. Discuss the challenge of incomplete data, correctly counting zero-event appearances and avoiding future information. Show the functional decomposition and planning PDFs briefly if the professor expects them in the recording. Confirm the exact December deadline. User acceptance, GitHub publication and a separate-machine installation are pending and must not be presented as completed.

