from google.adk.skills import models
from google.adk.tools.skill_toolset import SkillToolset
from ai_analytics_department.tools.data_loader import load_dataset
from ai_analytics_department.tools.eda import run_eda
from ai_analytics_department.tools.modeling import train_house_price_model
from ai_analytics_department.tools.visualization import create_saleprice_distribution, create_correlation_chart
from ai_analytics_department.tools.reporting import save_report_as_pdf

data_engineering_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="data-engineering",
        description="Load a CSV dataset into the shared DataFrame.",
    ),
    instructions="""Call load_dataset(file_path) with the provided file path to load the CSV into the shared DataFrame.
Output: {"status": "tool_called"}""",
)

data_analysis_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="data-analysis",
        description="Perform exploratory data analysis on the loaded dataset.",
    ),
    instructions="""Call run_eda() once to compute row count, column count, and missing values.
Then output JSON: {"summary": "...", "next_step": "SCIENTIST"}.
Never call run_eda twice. Set next_step to "SCIENTIST".""",
)

modeling_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="modeling",
        description="Train a RandomForest regression model on the loaded dataset.",
    ),
    instructions="""Call train_house_price_model(target_column="<column_name>") to train a RandomForestRegressor on the specified target column, then summarize the results. If no target column is specified, the last numeric column is used automatically.""",
)

business_reporting_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="business-reporting",
        description="Generate charts and a PDF business report.",
    ),
    instructions="""Call create_saleprice_distribution, create_correlation_chart, then save_report_as_pdf.
In your final output mention the saved chart file paths and the report location.""",
)


def create_data_engineer_toolset() -> SkillToolset:
    return SkillToolset(skills=[data_engineering_skill])


def create_data_analyst_toolset() -> SkillToolset:
    return SkillToolset(skills=[data_analysis_skill])


def create_data_scientist_toolset() -> SkillToolset:
    return SkillToolset(skills=[modeling_skill])


def create_business_analyst_toolset() -> SkillToolset:
    return SkillToolset(skills=[business_reporting_skill])
