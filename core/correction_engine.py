def suggest_gt_corrections(compare_df, confidence_threshold=0.85):

    suggestions = compare_df[
        (~compare_df["full_match"]) &
        (compare_df["confidence"] >= confidence_threshold)
    ]

    return suggestions
