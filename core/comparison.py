def compare_with_gt(llm_df, gt_df):

    merged = llm_df.merge(
        gt_df,
        on=["sentence_norm", "canonical_aspect"],
        how="left"
    )

    merged["category_match"] = (
        merged["aspect_categories"] == merged["aspect_categories_gt"]
    )

    merged["sentiment_match"] = (
        merged["sentiment"] == merged["sentiments"]
    )

    merged["tone_match"] = (
        merged["tones"] == merged["tones_gt"]
    )

    merged["full_match"] = (
        merged["category_match"] &
        merged["sentiment_match"] &
        merged["tone_match"]
    )

    return merged
