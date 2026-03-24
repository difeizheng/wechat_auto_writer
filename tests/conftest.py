"""
测试配置文件
"""
import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置测试环境变量
os.environ.setdefault('TESTING', 'true')
os.environ.setdefault('DASHSCOPE_API_KEY', 'test_api_key_for_testing')


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "api_key": "test_api_key_for_testing",
        "base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "default_model": "qwen-plus",
        "test_topic": "人工智能在医疗领域的应用",
        "test_template_type": "techTutorial",
    }


@pytest.fixture
def sample_article_outline():
    """示例文章大纲"""
    return {
        "title": "AI 医疗：开启智慧医疗新时代",
        "subtitle": "探索人工智能如何改变医疗健康产业",
        "sections": [
            {"title": "引言：AI 与医疗的相遇", "content": "介绍 AI 在医疗领域的发展现状和前景"},
            {"title": "AI 诊断：更精准、更高效", "content": "讲述 AI 在医学影像诊断、病理分析中的应用"},
            {"title": "智能治疗：个性化医疗方案", "content": "介绍 AI 如何帮助制定个性化治疗方案"},
            {"title": "药物研发：加速新药上市", "content": "讲述 AI 在药物发现、临床试验中的应用"},
            {"title": "未来展望：挑战与机遇并存", "content": "总结 AI 医疗面临的挑战和未来发展方向"}
        ],
        "suggested_cover": "医生与 AI 机器人协作的现代医疗场景"
    }


@pytest.fixture
def sample_article_content():
    """示例文章内容"""
    return """# AI 医疗：开启智慧医疗新时代

## 探索人工智能如何改变医疗健康产业

*生成时间：2026-03-24*

---

## 引言：AI 与医疗的相遇

近年来，人工智能技术在医疗领域的应用日益广泛...

## AI 诊断：更精准、更高效

医学影像是 AI 应用最成熟的领域之一...

## 智能治疗：个性化医疗方案

基于基因组学和临床数据，AI 可以为患者提供个性化治疗方案...

## 药物研发：加速新药上市

传统药物研发周期长、成本高，AI 技术的引入正在改变这一局面...

## 未来展望：挑战与机遇并存

尽管 AI 医疗前景广阔，但仍面临数据安全、算法透明度等挑战...
"""


@pytest.fixture
def temp_output_dir(tmp_path):
    """临时输出目录"""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """设置测试环境"""
    # 设置临时数据目录
    monkeypatch.setenv("TEST_DATA_DIR", str(tmp_path / "data"))
    # 创建临时目录
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "output").mkdir(exist_ok=True)
    return tmp_path
