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

class ServiceTester:
    def __init__(self, start_script, test_scripts, health_check_url="http://localhost:8102/health", timeout=300):
        self.start_script = start_script
        self.test_scripts = test_scripts
        self.health_check_url = health_check_url
        self.timeout = timeout
        self.service_process = None
        
        # 注册信号处理，确保服务能被正确终止
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """处理中断信号，确保服务进程被终止"""
        print(f"收到终止信号 {signum}，正在停止服务...")
        self.stop_service()
        sys.exit(0)
    
    def start_service(self):
        """启动 SGLang 服务"""
        print(f"启动 SGLang 服务: {self.start_script}")
        
        # 启动服务脚本作为子进程
        self.service_process = subprocess.Popen(
            self.start_script,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # 实时输出服务启动日志
        print("服务启动日志:")
        for line in iter(self.service_process.stdout.readline, ''):
            print(line, end='')
            if "The server is fired up and ready to roll" in line:  # 根据实际日志调整
                print("检测到服务启动完成标志")
                break
                
        return self.service_process.poll() is None  # 返回服务是否还在运行
    
    def wait_for_service_ready(self):
        """等待服务就绪"""
        print(f"等待服务在 {self.health_check_url} 上就绪...")
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            try:
                response = requests.get(self.health_check_url)
                if response.status_code == 200:
                    print("服务已就绪")
                    return True
            except Exception as e:
                print(f"服务尚未就绪: {e}，重试中...")
                
            time.sleep(5)  # 每隔5秒检查一次
            
        print(f"服务在 {self.timeout} 秒内未就绪，超时退出")
        return False
    
    def run_test(self):
        """运行 benchserving 测试"""
        if not self.service_process or self.service_process.poll() is not None:
            print("服务未运行，无法执行测试")
            return False
        
        all_success = True

        for test_script in self.test_scripts:
            print(f"\n==== 开始执行测试: {test_script} ====")
            
            # 运行测试脚本
            test_result = subprocess.run(
                test_script,
                shell=True,
                check=False,
                capture_output=True,
                text=True
            )
            
            # 输出测试结果
            print("测试标准输出:")
            print(test_result.stdout)
            
            if test_result.stderr:
                print("测试错误输出:")
                print(test_result.stderr)
                
            print(f"测试完成，返回代码: {test_result.returncode}")
            
            if test_result.returncode != 0:
                print(f"警告: 测试 {test_script} 失败")
                all_success = False
            else:
                print(f"测试 {test_script} 通过")
                
        return all_success
    
    def stop_service(self):
        """终止整个进程树（包括所有子进程）"""
        if self.service_process and self.service_process.poll() is None:
            print("终止 SGLang 服务及所有子进程...")
            
            try:
                # 获取主进程对象
                main_proc = psutil.Process(self.service_process.pid)
                
                # 递归获取所有子进程（包括孙子进程）
                all_procs = main_proc.children(recursive=True)
                all_procs.append(main_proc)  # 包含主进程本身
                
                # 先尝试优雅终止（SIGTERM）
                for proc in all_procs:
                    try:
                        proc.terminate()
                        print(f"已向进程 {proc.pid} 发送终止信号")
                    except psutil.NoSuchProcess:
                        print(f"进程 {proc.pid} 已终止")
                
                # 等待 10 秒，未终止则强制 kill（SIGKILL）
                gone, alive = psutil.wait_procs(all_procs, timeout=10)
                
                if alive:
                    print(f"以下进程未响应终止信号，强制终止：{[p.pid for p in alive]}")
                    for proc in alive:
                        try:
                            proc.kill()
                            print(f"已强制终止进程 {proc.pid}")
                        except psutil.NoSuchProcess:
                            pass
                
                print("服务及所有子进程已终止")
                return True
                
            except psutil.NoSuchProcess:
                print("主进程已不存在，可能已终止")
                return True
            except Exception as e:
                print(f"终止进程树失败：{e}")
                return False
        else:
            print("服务未运行或已终止")
            return True
    
    def run(self):
        """执行完整测试流程"""
        try:
            # 启动服务
            service_started = self.start_service()
            if not service_started:
                print("服务启动失败")
                return False
                
            # 等待服务就绪
            service_ready = self.wait_for_service_ready()
            if not service_ready:
                self.stop_service()
                return False
                
            # 运行测试
            test_success = self.run_test()
            
            # 停止服务
            self.stop_service()
            
            return test_success
            
        except Exception as e:
            print(f"执行过程中发生错误: {e}")
            self.stop_service()
            return False


def main():
    parser = argparse.ArgumentParser(description='SGLang 服务测试协调器')
    parser.add_argument('--start-script', required=True, help='启动 SGLang 服务的脚本')
    parser.add_argument('--test-scripts', nargs='+', required=True, help='执行测试的脚本列表，用空格分隔')
    parser.add_argument('--health-url', default='http://localhost:30000/health', help='服务健康检查 URL')
    parser.add_argument('--timeout', type=int, default=300, help='服务启动超时时间（秒）')
    
    args = parser.parse_args()
    
    tester = ServiceTester(
        start_script=args.start_script,
        test_scripts=args.test_scripts,
        health_check_url=args.health_url,
        timeout=args.timeout
    )
    
    success = tester.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
