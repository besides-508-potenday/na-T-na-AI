# -*- coding: utf-8 -*-

import requests
import json
import time
import psutil
import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from langchain_naver import ChatClovaX
from dotenv import load_dotenv
import threading
import queue

# 환경 변수 로드
load_dotenv()

class DirectAPIExecutor:
    """직접 API 호출 클래스"""
    def __init__(self, host: str, api_key: str, request_id: str):
        self._host = host
        self._api_key = api_key
        self._request_id = request_id

    def execute(self, completion_request: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            'Authorization': self._api_key,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json'  # 스트리밍 대신 일반 응답으로 변경
        }

        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        first_token_time = None
        response_text = ""
        total_tokens = 0
        
        try:
            response = requests.post(
                self._host + '/v3/chat-completions/HCX-007',
                headers=headers, 
                json=completion_request,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('result', {}).get('message', {}).get('content', '')
                total_tokens = result.get('result', {}).get('outputLength', 0)
                first_token_time = time.time() - start_time  # 첫 토큰까지의 시간
            else:
                print(f"API Error: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            print(f"Request failed: {e}")
            return None
        
        end_time = time.time()
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        total_time = end_time - start_time
        tps = total_tokens / total_time if total_time > 0 else 0
        
        return {
            'response_text': response_text,
            'total_time': total_time,
            'ttft': first_token_time,
            'total_tokens': total_tokens,
            'tps': tps,
            'memory_usage': memory_after - memory_before
        }

class LangChainExecutor:
    """LangChain 실행 클래스"""
    def __init__(self, api_key: str):
        self.chat = ChatClovaX(
            model="HCX-007",
            temperature=0.5,
            max_completion_tokens=256,
            api_key=api_key
        )

    def execute(self, messages: List[tuple]) -> Dict[str, Any]:
        start_time = time.time()
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            response = self.chat.invoke(messages)
            first_token_time = time.time() - start_time  # 첫 토큰까지의 시간
            
            response_text = response.content
            # LangChain에서는 토큰 수를 직접 제공하지 않으므로 대략적으로 계산
            total_tokens = len(response_text.split()) * 1.3  # 대략적인 토큰 수 추정
            
        except Exception as e:
            print(f"LangChain request failed: {e}")
            return None
        
        end_time = time.time()
        memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        total_time = end_time - start_time
        tps = total_tokens / total_time if total_time > 0 else 0
        
        return {
            'response_text': response_text,
            'total_time': total_time,
            'ttft': first_token_time,
            'total_tokens': total_tokens,
            'tps': tps,
            'memory_usage': memory_after - memory_before
        }

class PerformanceBenchmark:
    """성능 벤치마크 클래스"""
    
    def __init__(self):
        self.api_key = os.environ.get("CLOVASTUDIO_API_KEY")
        if not self.api_key:
            raise ValueError("CLOVASTUDIO_API_KEY 환경변수가 설정되지 않았습니다.")
        
        # 직접 API 실행기
        self.direct_executor = DirectAPIExecutor(
            host='https://clovastudio.stream.ntruss.com',
            api_key=f'Bearer {self.api_key}',
            request_id='benchmark_test_' + str(int(time.time()))
        )
        
        # LangChain 실행기
        self.langchain_executor = LangChainExecutor(self.api_key)
        
        # 테스트 메시지들
        self.test_messages = [
            "안녕하세요. 간단한 인사말 부탁드립니다.",
            "Python에서 리스트와 튜플의 차이점을 설명해주세요.",
            "머신러닝의 기본 개념과 주요 알고리즘 유형들에 대해 자세히 설명해주세요.",
            "클라우드 컴퓨팅의 장단점과 주요 서비스 모델(IaaS, PaaS, SaaS)에 대해 상세히 설명하고, 각각의 사용 사례를 예시와 함께 제시해주세요."
        ]

    def create_direct_api_request(self, message: str) -> Dict[str, Any]:
        """직접 API 요청 데이터 생성"""
        return {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message
                        }
                    ]
                }
            ],
            "topP": 0.8,
            "topK": 0,
            "maxTokens": 256,
            "temperature": 0.5,
            "repetitionPenalty": 1.1,
            "stop": [],
            "seed": 0,
            "includeAiFilters": True
        }

    def create_langchain_messages(self, message: str) -> List[tuple]:
        """LangChain 메시지 생성"""
        return [("user", message)]

    def run_benchmark(self, iterations: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """벤치마크 실행"""
        results = {
            'direct_api': [],
            'langchain': []
        }
        
        print(f"벤치마크 시작 - {iterations}회 반복 테스트")
        print("-" * 50)
        
        for i, message in enumerate(self.test_messages):
            print(f"\n테스트 {i+1}: {message[:50]}...")
            
            # 각 메시지에 대해 반복 테스트
            for iteration in range(iterations):
                print(f"  반복 {iteration + 1}/{iterations}")
                
                # Direct API 테스트
                print("    Direct API 테스트 중...")
                request_data = self.create_direct_api_request(message)
                direct_result = self.direct_executor.execute(request_data)
                if direct_result:
                    direct_result['message_length'] = len(message)
                    direct_result['test_case'] = i + 1
                    direct_result['iteration'] = iteration + 1
                    results['direct_api'].append(direct_result)
                
                # 잠시 대기 (API 제한 방지)
                time.sleep(1)
                
                # LangChain 테스트
                print("    LangChain 테스트 중...")
                langchain_messages = self.create_langchain_messages(message)
                langchain_result = self.langchain_executor.execute(langchain_messages)
                if langchain_result:
                    langchain_result['message_length'] = len(message)
                    langchain_result['test_case'] = i + 1
                    langchain_result['iteration'] = iteration + 1
                    results['langchain'].append(langchain_result)
                
                # 잠시 대기
                time.sleep(1)
        
        return results

    def analyze_results(self, results: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
        """결과 분석"""
        analysis_data = []
        
        for method, data in results.items():
            if data:
                df = pd.DataFrame(data)
                
                # 각 테스트 케이스별 통계
                for test_case in df['test_case'].unique():
                    case_data = df[df['test_case'] == test_case]
                    
                    analysis_data.append({
                        'method': method,
                        'test_case': test_case,
                        'avg_total_time': case_data['total_time'].mean(),
                        'avg_ttft': case_data['ttft'].mean(),
                        'avg_tps': case_data['tps'].mean(),
                        'avg_memory_usage': case_data['memory_usage'].mean(),
                        'avg_tokens': case_data['total_tokens'].mean(),
                        'std_total_time': case_data['total_time'].std(),
                        'message_length': case_data['message_length'].iloc[0]
                    })
        
        return pd.DataFrame(analysis_data)

    def create_visualizations(self, analysis_df: pd.DataFrame):
        """시각화 생성"""
        # 한글 폰트 설정
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Malgun Gothic', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Clova API Performance Comparison: Direct API vs LangChain', fontsize=16, fontweight='bold')
        
        methods = analysis_df['method'].unique()
        test_cases = analysis_df['test_case'].unique()
        
        # 색상 설정
        colors = {'direct_api': '#2E86AB', 'langchain': '#A23B72'}
        
        # 1. 총 응답 시간 비교
        ax1 = axes[0, 0]
        for method in methods:
            method_data = analysis_df[analysis_df['method'] == method]
            ax1.bar([f'Test {int(tc)}' for tc in method_data['test_case']], 
                   method_data['avg_total_time'], 
                   label=method.replace('_', ' ').title(), 
                   alpha=0.7, 
                   color=colors[method])
        ax1.set_title('Average Total Response Time')
        ax1.set_ylabel('Time (seconds)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. TTFT 비교
        ax2 = axes[0, 1]
        for method in methods:
            method_data = analysis_df[analysis_df['method'] == method]
            ax2.bar([f'Test {int(tc)}' for tc in method_data['test_case']], 
                   method_data['avg_ttft'], 
                   label=method.replace('_', ' ').title(), 
                   alpha=0.7, 
                   color=colors[method])
        ax2.set_title('Average Time To First Token (TTFT)')
        ax2.set_ylabel('Time (seconds)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. TPS 비교
        ax3 = axes[0, 2]
        for method in methods:
            method_data = analysis_df[analysis_df['method'] == method]
            ax3.bar([f'Test {int(tc)}' for tc in method_data['test_case']], 
                   method_data['avg_tps'], 
                   label=method.replace('_', ' ').title(), 
                   alpha=0.7, 
                   color=colors[method])
        ax3.set_title('Average Tokens Per Second (TPS)')
        ax3.set_ylabel('Tokens/second')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 메모리 사용량 비교
        ax4 = axes[1, 0]
        for method in methods:
            method_data = analysis_df[analysis_df['method'] == method]
            ax4.bar([f'Test {int(tc)}' for tc in method_data['test_case']], 
                   method_data['avg_memory_usage'], 
                   label=method.replace('_', ' ').title(), 
                   alpha=0.7, 
                   color=colors[method])
        ax4.set_title('Average Memory Usage')
        ax4.set_ylabel('Memory (MB)')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 5. 메시지 길이 vs 응답 시간
        ax5 = axes[1, 1]
        for method in methods:
            method_data = analysis_df[analysis_df['method'] == method]
            ax5.scatter(method_data['message_length'], 
                       method_data['avg_total_time'],
                       label=method.replace('_', ' ').title(),
                       s=100, 
                       alpha=0.7, 
                       color=colors[method])
        ax5.set_title('Message Length vs Response Time')
        ax5.set_xlabel('Message Length (characters)')
        ax5.set_ylabel('Response Time (seconds)')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # 6. 종합 성능 점수 (낮을수록 좋음)
        ax6 = axes[1, 2]
        performance_scores = []
        
        for method in methods:
            method_data = analysis_df[analysis_df['method'] == method]
            # 정규화된 점수 계산 (시간이 적을수록, TPS가 높을수록 좋음)
            normalized_time = method_data['avg_total_time'] / analysis_df['avg_total_time'].max()
            normalized_ttft = method_data['avg_ttft'] / analysis_df['avg_ttft'].max()
            normalized_memory = method_data['avg_memory_usage'] / analysis_df['avg_memory_usage'].max()
            normalized_tps = 1 - (method_data['avg_tps'] / analysis_df['avg_tps'].max())  # TPS는 높을수록 좋으므로 역수
            
            composite_score = (normalized_time + normalized_ttft + normalized_memory + normalized_tps) / 4
            
            ax6.bar([f'Test {int(tc)}' for tc in method_data['test_case']], 
                   composite_score, 
                   label=method.replace('_', ' ').title(), 
                   alpha=0.7, 
                   color=colors[method])
        
        ax6.set_title('Composite Performance Score\n(Lower is Better)')
        ax6.set_ylabel('Normalized Score')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()

    def print_summary(self, analysis_df: pd.DataFrame):
        """결과 요약 출력"""
        print("\n" + "="*80)
        print("성능 벤치마크 결과 요약")
        print("="*80)
        
        # 전체 평균 계산
        summary_stats = analysis_df.groupby('method').agg({
            'avg_total_time': 'mean',
            'avg_ttft': 'mean',
            'avg_tps': 'mean',
            'avg_memory_usage': 'mean',
            'avg_tokens': 'mean'
        }).round(4)
        
        print(f"\n전체 평균 성능:")
        print(f"{'Method':<15} {'Avg Time(s)':<12} {'Avg TTFT(s)':<12} {'Avg TPS':<10} {'Memory(MB)':<12} {'Tokens':<10}")
        print("-" * 75)
        
        for method, row in summary_stats.iterrows():
            print(f"{method.replace('_', ' ').title():<15} "
                  f"{row['avg_total_time']:<12.3f} "
                  f"{row['avg_ttft']:<12.3f} "
                  f"{row['avg_tps']:<10.1f} "
                  f"{row['avg_memory_usage']:<12.1f} "
                  f"{row['avg_tokens']:<10.1f}")
        
        # 승자 결정
        print(f"\n성능 비교 결과:")
        direct_stats = summary_stats.loc['direct_api']
        langchain_stats = summary_stats.loc['langchain']
        
        print(f"• 응답 속도: {'Direct API' if direct_stats['avg_total_time'] < langchain_stats['avg_total_time'] else 'LangChain'} 승리")
        print(f"• TTFT: {'Direct API' if direct_stats['avg_ttft'] < langchain_stats['avg_ttft'] else 'LangChain'} 승리")
        print(f"• TPS: {'Direct API' if direct_stats['avg_tps'] > langchain_stats['avg_tps'] else 'LangChain'} 승리")
        print(f"• 메모리 효율성: {'Direct API' if direct_stats['avg_memory_usage'] < langchain_stats['avg_memory_usage'] else 'LangChain'} 승리")
        
        # 개선 비율 계산
        time_improvement = ((langchain_stats['avg_total_time'] - direct_stats['avg_total_time']) / langchain_stats['avg_total_time']) * 100
        tps_improvement = ((direct_stats['avg_tps'] - langchain_stats['avg_tps']) / langchain_stats['avg_tps']) * 100
        
        print(f"\n개선 효과:")
        print(f"• Direct API가 LangChain보다 {abs(time_improvement):.1f}% {'빠름' if time_improvement > 0 else '느림'}")
        print(f"• Direct API가 LangChain보다 TPS {abs(tps_improvement):.1f}% {'높음' if tps_improvement > 0 else '낮음'}")

def main():
    """메인 실행 함수"""
    try:
        benchmark = PerformanceBenchmark()
        
        # 벤치마크 실행
        results = benchmark.run_benchmark(iterations=3)
        
        # 결과 분석
        analysis_df = benchmark.analyze_results(results)
        
        # 결과 출력
        benchmark.print_summary(analysis_df)
        
        # 시각화
        benchmark.create_visualizations(analysis_df)
        
        # 상세 결과를 CSV로 저장
        analysis_df.to_csv('clova_api_benchmark_results.csv', index=False)
        print(f"\n상세 결과가 'clova_api_benchmark_results.csv' 파일로 저장되었습니다.")
        
    except Exception as e:
        print(f"벤치마크 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()