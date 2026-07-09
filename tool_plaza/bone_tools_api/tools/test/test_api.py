"""API

Tool Call API Server
 http://localhost:8000
"""
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict

import httpx

# APIURL
BASE_URL = "http://localhost:8000"
CLIENT_TIMEOUT = 30.0  # ()


class APITester:
    """API"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=CLIENT_TIMEOUT)

        #
        limits = httpx.Limits(
            max_connections=10000,
            max_keepalive_connections=5000
        )
        self.async_client = httpx.AsyncClient(
            timeout=CLIENT_TIMEOUT,
            limits=limits
        )

    def __del__(self):
        """"""
        self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.async_client.aclose()

    def print_separator(self, title: str):
        """"""
        print("\n" + "=" * 80)
        print(f" {title}")
        print("=" * 80)

    def test_health(self):
        """"""
        self.print_separator("1: ")

        try:
            response = self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()

            print(f"OK: {data['status']}")
            print(f"OK: {data['tools_loaded']}")
            print(f"OK: {data['timestamp']}")
            return True

        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def test_list_tools(self):
        """"""
        self.print_separator("2: ")

        try:
            response = self.client.get(f"{self.base_url}/tools")
            response.raise_for_status()
            data = response.json()

            print(f"OK: {data['total_tools']}")
            print(f"OK statistics:")
            for category, count in data['categories'].items():
                print(f" - {category}: {count}")

            print(f"\nTop 10:")
            for tool_name in data['tools'][:10]:
                print(f" - {tool_name}")

            return True

        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def test_get_tool_schema(self):
        """Schema"""
        self.print_separator("3: Schema")

        test_tools = ["echo", "cpubmed.search", "medibook.search", "semanticscholar.search"]

        for tool_name in test_tools:
            try:
                response = self.client.get(f"{self.base_url}/tools/{tool_name}")
                response.raise_for_status()
                schema = response.json()

                print(f"\nOK: {schema['function']['name']}")
                print(f": {schema['function']['description'][:50]}...")
                print(f": {list(schema['function']['parameters']['properties'].keys())}")

            except Exception as e:
                print(f"ERROR Schema [{tool_name}]: {e}")
                return False

        return True

    def test_execute_echo(self):
        """Echo"""
        self.print_separator("4: Echo")

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

            print(f"OK: {data['success']}")
            print(f"OK: {data['data']}")
            print(f"OK: {data['execution_time']:.3f}")

            return True

        except Exception as e:
            print(f"ERROR Echo: {e}")
            return False

    def test_execute_cpubmed(self):
        """CPubMed"""
        self.print_separator("5: CPubMed")

        try:
            payload = {
                "tool_name": "cpubmed.search",
                "parameters": {
                    "entity": "",
                    "relation": "",
                    "limit": 5
                }
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"OK: {data['success']}")
            print(f"OK: {data['execution_time']:.3f}")

            if data['success']:
                result = json.loads(data['data'])
                print(f"OK results: {result['total_results']}")
                if result.get('relations'):
                    print(f"OK: {list(result['relations'].keys())}")

            return True

        except Exception as e:
            print(f"ERROR CPubMed: {e}")
            return False

    def test_execute_fuzzy_search(self):
        """"""
        self.print_separator("6: ")

        try:
            payload = {
                "tool_name": "cpubmed.fuzzy_search",
                "parameters": {
                    "keyword": "",
                    "threshold": 0.6,
                    "limit": 3
                }
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"OK: {data['success']}")
            print(f"OK: {data['execution_time']:.3f}")

            if data['success']:
                result = json.loads(data['data'])
                print(f"OK: {result['total_matches']}")
                for match in result['matches'][:3]:
                    print(f" - {match['entity']} (: {match['similarity']})")

            return True

        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def test_execute_relation_tool(self):
        """"""
        self.print_separator("7: ")

        try:
            payload = {
                "tool_name": "cpubmed.query_drug_treatment",
                "parameters": {
                    "entity": "",
                    "limit": 3
                }
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"OK: {data['success']}")
            print(f"OK: {data['execution_time']:.3f}")

            if data['success']:
                result = json.loads(data['data'])
                print(f"OK results: {result['total_results']}")
                for item in result['results'][:3]:
                    print(f" - {item.get('target', '')}")

            return True

        except Exception as e:
            print(f"ERROR: {e}")
            return False

    async def test_concurrent_requests(self, num_requests: int = 2000):
        """"""
        self.print_separator(f"8: ({num_requests})")

        async def make_request(i: int):
            """"""
            try:
                payload = {
                    "tool_name": "echo",
                    "parameters": {
                        "message": f" #{i}",
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

        #
        start_time = time.time()
        tasks = [make_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time
        success_count = sum(1 for success, _ in results if success)
        avg_time = sum(t for _, t in results) / len(results) if results else 0

        print(f"OK: {num_requests}")
        print(f"OK: {success_count}")
        print(f"OK: {num_requests - success_count}")
        print(f"OK: {total_time:.3f}")
        print(f"OK: {avg_time:.3f}")
        print(f"OK QPS: {num_requests / total_time:.2f}")

        return success_count == num_requests

    def test_database_summary(self):
        """"""
        self.print_separator("9: ")

        try:
            payload = {
                "tool_name": "cpubmed.get_summary",
                "parameters": {}
            }

            response = self.client.post(f"{self.base_url}/tools/execute", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"OK: {data['success']}")

            if data['success']:
                summary = json.loads(data['data'])
                print(f"OK: {summary['database']}")
                print(f"OK: {summary['statistics']['total_triples']}")
                print(f"OK: {summary['statistics']['total_entities']}")
                print(f"OK: {summary['statistics']['relation_types']}")

            return True

        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def test_semanticscholar_search(self):
        """Semantic Scholar"""
        self.print_separator("10: Semantic Scholar")

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

            print(f"OK: {data['success']}")
            print(f"OK: {data['execution_time']:.3f}")

            if data['success']:
                result = json.loads(data['data'])
                print(f"OK: {result['query']}")
                print(f"OK results: {result['total_results']}")
                print(f"OK: {result['returned_count']}")

                if result.get('papers'):
                    print(f"\nTop 3:")
                    for i, paper in enumerate(result['papers'][:3], 1):
                        print(f" {i}. {paper.get('title', 'N/A')[:60]}...")
                        print(f": {', '.join(paper.get('authors', [])[:3])}")
                        print(f": {paper.get('year', 'N/A')}")

            return True

        except Exception as e:
            print(f"ERROR Semantic Scholar: {e}")
            return False


async def main():
    """"""
    print("=" * 80)
    print(" Tool Call API Server ")
    print("=" * 80)
    print(f"\nBase URL: {BASE_URL}")
    print("...")

    tester = APITester()
    results = []

    #
    results.append(("", tester.test_health()))
    results.append(("", tester.test_list_tools()))
    results.append(("Schema", tester.test_get_tool_schema()))
    results.append(("Echo", tester.test_execute_echo()))
    results.append(("CPubMed", tester.test_execute_cpubmed()))
    results.append(("", tester.test_execute_fuzzy_search()))
    results.append(("", tester.test_execute_relation_tool()))
    results.append(("", tester.test_database_summary()))
    results.append(("Semantic Scholar", tester.test_semanticscholar_search()))

    #
    async with APITester() as async_tester:
        concurrent_result = await async_tester.test_concurrent_requests(num_requests=2000)
        results.append(("", concurrent_result))

    # statisticsresult
    print("\n" + "=" * 80)
    print(" result")
    print("=" * 80)

    success_count = sum(1 for _, success in results if success)
    total_count = len(results)

    for test_name, success in results:
        status = "OK " if success else "ERROR "
        print(f"{status} - {test_name}")

    print("\n" + "=" * 80)
    print(f": {success_count}/{total_count} ")
    print("=" * 80)

    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
