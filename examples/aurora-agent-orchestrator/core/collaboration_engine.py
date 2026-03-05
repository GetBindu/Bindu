def collaboration_pipeline(task_description):

    pipeline = []

    if "research" in task_description.lower():
        pipeline.append("research_agent")

    if "finance" in task_description.lower() or "earnings" in task_description.lower():
        pipeline.append("finance_agent")

    pipeline.append("summary_agent")

    return pipeline