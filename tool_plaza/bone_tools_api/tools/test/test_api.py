"""API测试脚本

测试Tool Call API Server的所有端点
假设服务器已在 http://YOUR_HOST:YOUR_PORT 运行
"""
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict

import httpx

# API基础URL
BASE_URL = "http://YOUR_HOST:YOUR_PORT"
CLIENT_TIMEOUT = 30.0  # 请求超时时间（秒）


class APITester:
    """API测试类"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=CLIENT_TIMEOUT)

        # 增大连接池以支持高并发压力测试
        limits = httpx.Limits(
            max_connections=10000,
            max_keepalive_connections=5000
        )
        self.async_client = httpx.AsyncClient(
            timeout=CLIENT_TIMEOUT,
            limits=limits
        )

    def __del__(self):
        """清理资源"""
        self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.async_client.aclose()

    def print_separator(self, title: str):
        """打印分隔符"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def test_health(self):
        """测试健康检查"""
        self.print_separator("测试1: 健康检查")

        try:
            response = self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()

            print(f"✓ 状态: {data['status']}")
            print(f"✓ 工具数量: {data['tools_loaded']}")
            print(f"✓ 时间戳: {data['timestamp']}")
            return True

        except Exception as e:
            print(f"✗ 健康检查失败: {e}")
            return False

    def test_list_tools(self):
        """测试获取工具列表"""
        self.print_separator("测试2: 获取工具列表")

        try:
            response = self.client.get(f"{self.base_url}/tools")
            response.raise_for_status()
            data = response.json()

            print(f"✓ 工具总数: {data['total_tools']}")
            print(f"✓ 分类统计:")
            for category, count in data['categories'].items():
                print(f"    - {category}: {count}个")

            print(f"\n前10个工具:")
            for tool_name in data['tools'][:10]:
                print(f"    - {tool_name}")

            return True

        except Exception as e:
            print(f"✗ 获取工具列表失败: {e}")
            return False

    def test_get_tool_schema(self):
        """测试获取工具Schema"""
        self.print_separator("测试3: 获取工具Schema")

        test_tools = ["echo", "cpubmed.search", "medibook.search", "semanticscholar.search"]

        for tool_name in test_tools:
            try:
                response = self.client.get(f"{self.base_url}/tools/{tool_name}")
                response.raise_for_status()
                schema = response.json()

                print(f"\n✓ 工具: {schema['function']['name']}")
                print(f"  描述: {schema['function']['description'][:50]}...")
                print(f"  参数: {list(schema['function']['parameters']['properties'].keys())}")

            except Exception as e:
                print(f"✗ 获取工具Schema失败 [{tool_name}]: {e}")
                return False

        return True

    def test_execute_echo(self):
        """测试执行Echo工具"""
        self.print_separator("测试4: 执行Echo工具")

        try:
            payload = {
                "tool_name": "echo",
                "parameters": {
                    "message": "Hello API!",
                    "repeat": 3
                }
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"✓ 执行成功: {data['success']}")
            print(f"✓ 返回数据: {data['data']}")
            print(f"✓ 执行时间: {data['execution_time']:.3f}秒")

            return True

        except Exception as e:
            print(f"✗ 执行Echo工具失败: {e}")
            return False

    def test_execute_cpubmed(self):
        """测试执行CPubMed工具"""
        self.print_separator("测试5: 执行CPubMed工具")

        try:
            payload = {
                "tool_name": "cpubmed.search",
                "parameters": {
                    "entity": "糖尿病",
                    "relation": "药物治疗",
                    "limit": 5
                }
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"✓ 执行成功: {data['success']}")
            print(f"✓ 执行时间: {data['execution_time']:.3f}秒")

            if data['success']:
                result = json.loads(data['data'])
                print(f"✓ 找到结果: {result['total_results']}条")
                if result.get('relations'):
                    print(f"✓ 关系类型: {list(result['relations'].keys())}")

            return True

        except Exception as e:
            print(f"✗ 执行CPubMed工具失败: {e}")
            return False

    def test_execute_fuzzy_search(self):
        """测试模糊搜索工具"""
        self.print_separator("测试6: 模糊搜索")

        try:
            payload = {
                "tool_name": "cpubmed.fuzzy_search",
                "parameters": {
                    "keyword": "肺癌",
                    "threshold": 0.6,
                    "limit": 3
                }
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"✓ 执行成功: {data['success']}")
            print(f"✓ 执行时间: {data['execution_time']:.3f}秒")

            if data['success']:
                result = json.loads(data['data'])
                print(f"✓ 匹配数量: {result['total_matches']}")
                for match in result['matches'][:3]:
                    print(f"    - {match['entity']} (相似度: {match['similarity']})")

            return True

        except Exception as e:
            print(f"✗ 模糊搜索失败: {e}")
            return False

    def test_execute_relation_tool(self):
        """测试关系专用工具"""
        self.print_separator("测试7: 关系专用工具")

        try:
            payload = {
                "tool_name": "cpubmed.query_drug_treatment",
                "parameters": {
                    "entity": "高血压",
                    "limit": 3
                }
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"✓ 执行成功: {data['success']}")
            print(f"✓ 执行时间: {data['execution_time']:.3f}秒")

            if data['success']:
                result = json.loads(data['data'])
                print(f"✓ 结果数量: {result['total_results']}")
                for item in result['results'][:3]:
                    print(f"    - {item.get('target', '')}")

            return True

        except Exception as e:
            print(f"✗ 关系专用工具失败: {e}")
            return False

    async def test_concurrent_requests(self, num_requests: int = 2000):
        """测试并发请求"""
        self.print_separator(f"测试8: 并发请求 ({num_requests}个)")

        async def make_request(i: int):
            """发送单个请求"""
            try:
                payload = {
                    "tool_name": "echo",
                    "parameters": {
                        "message": f"并发测试 #{i}",
                        "repeat": 1
                    }
                }

                response = await self.async_client.post(
                    f"{self.base_url}/tools/execute",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data['success'], data['execution_time']

            except Exception as e:
                return False, 0.0

        # 发送并发请求
        start_time = time.time()
        tasks = [make_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time
        success_count = sum(1 for success, _ in results if success)
        avg_time = sum(t for _, t in results) / len(results) if results else 0

        print(f"✓ 总请求数: {num_requests}")
        print(f"✓ 成功数: {success_count}")
        print(f"✓ 失败数: {num_requests - success_count}")
        print(f"✓ 总耗时: {total_time:.3f}秒")
        print(f"✓ 平均单个请求耗时: {avg_time:.3f}秒")
        print(f"✓ QPS: {num_requests / total_time:.2f}")

        return success_count == num_requests

    def test_database_summary(self):
        """测试数据库概览"""
        self.print_separator("测试9: 数据库概览")

        try:
            payload = {
                "tool_name": "cpubmed.get_summary",
                "parameters": {}
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"✓ 执行成功: {data['success']}")

            if data['success']:
                summary = json.loads(data['data'])
                print(f"✓ 数据库: {summary['database']}")
                print(f"✓ 三元组数: {summary['statistics']['total_triples']}")
                print(f"✓ 实体数: {summary['statistics']['total_entities']}")
                print(f"✓ 关系类型数: {summary['statistics']['relation_types']}")

            return True

        except Exception as e:
            print(f"✗ 数据库概览失败: {e}")
            return False

    def test_semanticscholar_search(self):
        """测试Semantic Scholar论文搜索"""
        self.print_separator("测试10: Semantic Scholar论文搜索")

        try:
            payload = {
                "tool_name": "semanticscholar.search",
                "parameters": {
                    "query": "machine learning",
                    "limit": 5
                }
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"✓ 执行成功: {data['success']}")
            print(f"✓ 执行时间: {data['execution_time']:.3f}秒")

            if data['success']:
                result = json.loads(data['data'])
                print(f"✓ 查询关键词: {result['query']}")
                print(f"✓ 总结果数: {result['total_results']}")
                print(f"✓ 返回数量: {result['returned_count']}")

                if result.get('papers'):
                    print(f"\n前3篇论文:")
                    for i, paper in enumerate(result['papers'][:3], 1):
                        print(f"  {i}. {paper.get('title', 'N/A')[:60]}...")
                        print(f"     作者: {', '.join(paper.get('authors', [])[:3])}")
                        print(f"     年份: {paper.get('year', 'N/A')}")

            return True

        except Exception as e:
            print(f"✗ Semantic Scholar搜索失败: {e}")
            return False


async def main():
    """运行所有测试"""
    print("=" * 80)
    print("  Tool Call API Server 测试套件")
    print("=" * 80)
    print(f"\n目标服务器: {BASE_URL}")
    print("假设服务器已在运行...")

    tester = APITester()
    results = []

    # 同步测试
    results.append(("健康检查", tester.test_health()))
    results.append(("工具列表", tester.test_list_tools()))
    results.append(("工具Schema", tester.test_get_tool_schema()))
    results.append(("Echo工具", tester.test_execute_echo()))
    results.append(("CPubMed工具", tester.test_execute_cpubmed()))
    results.append(("模糊搜索", tester.test_execute_fuzzy_search()))
    results.append(("关系专用工具", tester.test_execute_relation_tool()))
    results.append(("数据库概览", tester.test_database_summary()))
    results.append(("Semantic Scholar搜索", tester.test_semanticscholar_search()))

    # 异步并发测试
    async with APITester() as async_tester:
        concurrent_result = await async_tester.test_concurrent_requests(num_requests=2000)
        results.append(("并发测试", concurrent_result))

    # 统计结果
    print("\n" + "=" * 80)
    print("  测试结果汇总")
    print("=" * 80)

    success_count = sum(1 for _, success in results if success)
    total_count = len(results)

    for test_name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status} - {test_name}")

    print("\n" + "=" * 80)
    print(f"总计: {success_count}/{total_count} 测试通过")
    print("=" * 80)

    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
