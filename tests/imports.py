try:
    # Replace 'Agent' or 'Workflow' with the specific class you want to check
    # from google.adk.agents.workflow.workflow_agent import WorkflowAgent
    # Import the specific orchestration agent you need
    from google.adk.agents.workflow import WorkflowAgent

    print("Success: 'WorkflowAgent' exists and is ready to use.")
except ImportError as e:
    print(f"Import failed: {e}")

