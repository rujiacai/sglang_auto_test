#!/usr/bin/env python3
import os
import subprocess
import time
import argparse
import requests
import signal
import sys
from pathlib import Path
import psutil
import threading
import logging
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceTestSuite:
    """管理一组服务和对应的测试脚本"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service_process = None
        self.success = False
        self.test_results = {}
        self.log_thread = None
        self.log_buffer = []
        self.service_ready = threading.Event()
        
    def start_service(self) -> bool:
        """启动服务"""
        logger.info(f"启动服务: {self.config['name']}")
        
        try:
            # 使用pty创建伪终端，避免输出缓冲问题
            import pty
            master, slave = pty.openpty()
            
            self.service_process = subprocess.Popen(
                self.config['start_script'],
                shell=True,
                stdout=slave,
                stderr=slave,
                close_fds=True,
                universal_newlines=True
            )
            
            # 关闭从端，主端用于读取
            os.close(slave)
            
            # 启动日志处理线程
            self.log_thread = threading.Thread(target=self._process_service_logs, args=(master,))
            self.log_thread.daemon = True
            self.log_thread.start()
            
            # 等待服务启动完成或超时
            start_time = time.time()
            ready_pattern = self.config.get('ready_pattern')
            
            if ready_pattern:
                logger.info(f"等待服务就绪信号: {ready_pattern}")
                while time.time() - start_time < self.config.get('timeout', 300):
                    if self.service_ready.is_set():
                        logger.info(f"服务 {self.config['name']} 启动完成")
                        return True
                    time.sleep(0.5)
                    
                logger.error(f"服务 {self.config['name']} 启动超时，未收到就绪信号")
                return False
            else:
                # 如果没有就绪模式，等待一段时间后继续
                logger.info("未配置就绪检测模式，使用默认等待时间")
                time.sleep(10)  # 默认等待10秒
                return True
                
        except Exception as e:
            logger.error(f"启动服务失败: {e}")
            return False
    
    def _process_service_logs(self, master_fd):
        """异步处理服务日志"""
        if not master_fd:
            return
            
        try:
            with os.fdopen(master_fd, 'r') as f:
                for line in iter(f.readline, ''):
                    line = line.strip()
                    self.log_buffer.append(line)
                    logger.info(line)
                    
                    # 检查服务就绪模式
                    ready_pattern = self.config.get('ready_pattern')
                    if ready_pattern and ready_pattern in line:
                        self.service_ready.set()
                        
                    # 限制缓冲区大小，防止内存溢出
                    if len(self.log_buffer) > 1000:
                        self.log_buffer.pop(0)
        except Exception as e:
            logger.error(f"处理服务日志时出错: {e}")
        finally:
            if master_fd:
                try:
                    os.close(master_fd)
                except:
                    pass
    
    def wait_for_service_ready(self) -> bool:
        """等待服务就绪"""
        if not self.config.get('health_check'):
            logger.info("跳过健康检查（配置中未指定）")
            return True
            
        logger.info(f"等待服务 {self.config['name']} 在 {self.config['health_check']} 上就绪...")
        start_time = time.time()
        
        while time.time() - start_time < self.config.get('timeout', 300):
            try:
                response = requests.get(self.config['health_check'], timeout=5)
                if response.status_code == 200:
                    logger.info(f"服务 {self.config['name']} 已就绪")
                    return True
            except Exception as e:
                logger.debug(f"服务尚未就绪: {e}")
                
            time.sleep(1)  # 更频繁地检查
            
        logger.error(f"服务 {self.config['name']} 在超时时间内未就绪")
        return False
    
    def run_tests(self) -> bool:
        """运行所有测试脚本"""
        if not self.service_process or self.service_process.poll() is not None:
            logger.error(f"服务 {self.config['name']} 未运行，无法执行测试")
            return False
            
        all_success = True
        
        for test_name, test_script in self.config['test_scripts'].items():
            logger.info(f"\n==== 开始执行测试: {self.config['name']} - {test_name} ====")
            
            # 运行测试脚本
            try:
                test_result = subprocess.run(
                    test_script,
                    shell=True,
                    check=False,
                    capture_output=True,
                    text=True,
                    # timeout=300  # 设置测试超时时间
                )
            except subprocess.TimeoutExpired as e:
                logger.error(f"测试 {test_name} 超时")
                return False
                
            # 记录测试结果
            self.test_results[test_name] = {
                'returncode': test_result.returncode,
                'stdout': test_result.stdout,
                'stderr': test_result.stderr,
                'success': test_result.returncode == 0
            }
            
            # 输出测试结果
            logger.info(f"测试 {test_name} 标准输出:")
            for line in test_result.stdout.splitlines():
                logger.info(line)
                
            if test_result.stderr:
                logger.warning(f"测试 {test_name} 错误输出:")
                for line in test_result.stderr.splitlines():
                    logger.warning(line)
                
            logger.info(f"测试 {test_name} 完成，返回代码: {test_result.returncode}")
            
            if test_result.returncode != 0:
                logger.error(f"测试 {test_name} 失败")
                all_success = False
            else:
                logger.info(f"测试 {test_name} 通过")
                
        return all_success
    
    def stop_service(self) -> bool:
        """停止服务"""
        if not self.service_process or self.service_process.poll() is not None:
            logger.info(f"服务 {self.config['name']} 未运行或已停止")
            return True
            
        logger.info(f"停止服务: {self.config['name']}")
        
        try:
            # 获取主进程
            main_process = psutil.Process(self.service_process.pid)
            
            # 获取所有子进程（递归）
            children = main_process.children(recursive=True)
            
            # 先终止所有子进程
            for child in children:
                logger.info(f"终止子进程: {child.pid} ({child.name()})")
                child.terminate()
                
            # 等待子进程结束
            _, still_alive = psutil.wait_procs(children, timeout=5)
            
            # 强制杀死仍在运行的子进程
            for child in still_alive:
                logger.warning(f"强制终止子进程: {child.pid} ({child.name()})")
                child.kill()
                
            # 终止主进程
            self.service_process.terminate()
            try:
                self.service_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.service_process.kill()
                self.service_process.wait()
                
            # 等待日志线程完成
            if self.log_thread and self.log_thread.is_alive():
                self.log_thread.join(timeout=2.0)
                
            logger.info(f"服务 {self.config['name']} 已成功停止")
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"停止服务 {self.config['name']} 时进程操作错误: {e}")
            return False
        except Exception as e:
            logger.error(f"停止服务 {self.config['name']} 时发生未知错误: {e}")
            return False
    
    def run(self) -> bool:
        """执行完整测试流程"""
        try:
            # 启动服务
            service_started = self.start_service()
            if not service_started:
                logger.error(f"服务 {self.config['name']} 启动失败")
                return False
                
            # 等待服务就绪
            service_ready = self.wait_for_service_ready()
            if not service_ready:
                self.stop_service()
                return False
                
            # 运行测试
            test_success = self.run_tests()
            
            # 停止服务
            self.stop_service()
            
            self.success = test_success
            return test_success
            
        except Exception as e:
            logger.error(f"执行服务 {self.config['name']} 测试套件时发生错误: {e}")
            self.stop_service()
            return False

class MultiServiceTester:
    """管理多个服务测试套件"""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.suites = []
        self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        try:
            # 简单实现：假设配置文件是 JSON 格式
            # 实际应用中可以支持 YAML 等其他格式
            import json
            with open(self.config_file, 'r') as f:
                configs = json.load(f)
                
            for config in configs:
                self.suites.append(ServiceTestSuite(config))
                
            logger.info(f"成功加载 {len(self.suites)} 个服务测试套件")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            sys.exit(1)
    
    def run_serial(self) -> bool:
        """串行执行所有测试套件"""
        all_success = True
        
        for suite in self.suites:
            success = suite.run()
            if not success:
                all_success = False
                
        return all_success
    
    def run_parallel(self) -> bool:
        """并行执行所有测试套件"""
        threads = []
        
        for suite in self.suites:
            thread = threading.Thread(target=suite.run)
            thread.start()
            threads.append(thread)
            
        # 等待所有线程完成
        for thread in threads:
            thread.join()
            
        # 检查所有套件是否成功
        return all([suite.success for suite in self.suites])
    
    def generate_report(self, output_file: str = None):
        """生成测试报告"""
        report = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'total_suites': len(self.suites),
            'success_suites': sum([1 for s in self.suites if s.success]),
            'suites': []
        }
        
        for suite in self.suites:
            suite_report = {
                'name': suite.config['name'],
                'success': suite.success,
                'test_results': suite.test_results
            }
            report['suites'].append(suite_report)
            
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(report, f, indent=2, ensure_ascii=False)
                logger.info(f"测试报告已保存到 {output_file}")
            except Exception as e:
                logger.error(f"保存测试报告失败: {e}")
                
        return report

def main():
    parser = argparse.ArgumentParser(description='SGLang 多服务多测试协调器')
    parser.add_argument('--config', required=True, help='配置文件路径')
    parser.add_argument('--parallel', action='store_true', help='并行执行测试套件')
    parser.add_argument('--report', help='输出测试报告的文件路径')
    
    args = parser.parse_args()
    
    tester = MultiServiceTester(args.config)
    
    logger.info(f"开始执行测试，模式: {'并行' if args.parallel else '串行'}")
    success = tester.run_parallel() if args.parallel else tester.run_serial()
    
    if args.report:
        tester.generate_report(args.report)
    
    logger.info(f"所有测试完成，整体结果: {'成功' if success else '失败'}")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()    