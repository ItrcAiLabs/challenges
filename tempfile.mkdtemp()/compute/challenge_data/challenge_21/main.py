import sys
import pandas as pd
import traceback
def evaluate(test_annotation_file ,user_annotation_file, phase_name, **kwargs):
    score = 0
    original_file = pd.read_csv(test_annotation_file)
    original_stance = original_file['Stance']

    user_file = pd.read_csv(user_annotation_file)
    user_stance = user_file['Stance']

    # displaying selected columns (Country and Capital)
    for org_stance, usr_stance in zip(original_stance, user_stance):
        if usr_stance == org_stance:
            score += 1
    result = {}
    try:
        result['result'] = [
            {
                'split1': {
                    'score': score,
                }
            },
            {
                'split2': {
                    'score': score,
                }
            }
        ]
        result['submission_metadata'] = "This submission metadata will only be shown to the Challenge Host"
        result['submission_result'] = "This is the actual result to show to the participant once submission is finished"
        return result
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
        return e


