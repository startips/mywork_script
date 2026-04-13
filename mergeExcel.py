import os
import zipfile
import shutil
import subprocess
from pathlib import Path
from interface import excel


def mergeData():  # 汇总所有数据到
    # --- 配置区域 ---
    source_dir = '/Users/shadowx/Documents/招行/巡检/2026Q1/20260324'  # 存放压缩包的目录
    output_file = 'data/巡检成功数据汇总'  # 输出文件名
    temp_extract_dir = '/Users/shadowx/Documents/招行/巡检/2026Q1/20260324/temp_extract'  # 临时解压目录
    target_sub_path = "NetWork Healthy Check Report(Engineer).xlsx"  # 目标文件
    dataall = []
    if not os.path.exists(source_dir):
        print(f"❌ 错误: 找不到目录 {source_dir}")
        return
    # 初始化临时目录
    if os.path.exists(temp_extract_dir):
        shutil.rmtree(temp_extract_dir)
    os.makedirs(temp_extract_dir)
    zip_files = [f for f in os.listdir(source_dir) if f.endswith('.zip')]
    for zip_name in zip_files:
        print(f"\n📦 正在处理: {zip_name}")
        zip_path = os.path.join(source_dir, zip_name)
        try:
            # 修复点 3: 专门处理子目录名，去掉空格等可能引起路径解析问题的字符
            sub_folder_name = zip_name.replace('.zip', '').strip()
            extract_sub_dir = os.path.join(temp_extract_dir, sub_folder_name)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 修复点 4: 处理中文压缩包乱码（Windows 压缩包在 Mac 上常有的问题）
                for member in zip_ref.namelist():
                    try:
                        # 尝试将文件名从 cp437 (zip 标准) 转为 gbk 再转 utf-8
                        filename = member.encode('cp437').decode('gbk')
                    except:
                        filename = member
                    # 组合成解压后的实际路径
                    dest_path = os.path.join(extract_sub_dir, filename)
                    # 确保父目录存在
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    # 如果不是文件夹，则写入文件
                    if not filename.endswith('/'):
                        with zip_ref.open(member) as source, open(dest_path, "wb") as target:
                            shutil.copyfileobj(source, target)
            # --- 调试打印：让你看清楚解压后到底路径长啥样 ---
            print(f"  📂 已解压到: {extract_sub_dir}")
            # 修复点 5: 使用更加鲁棒的查找方式
            # rglob("**/文件名.xlsx") 会忽略中间所有复杂的文件夹名（包括乱码的文件夹）
            target_paths = list(Path(extract_sub_dir).rglob(f"**/{target_sub_path}"))
            if target_paths:  # 处理数据部分
                # 打印出真正找到的路径，方便你核对
                actual_file_path = target_paths[0]
                print(f"  ✅ 找到文件: {actual_file_path.relative_to(extract_sub_dir)}")
                readData = excel(target_paths[0])
                dataList = readData.excel_read(row_start=3)
                dataall.extend(dataList)
            else:
                print(f"  ⚠️ [跳过] 在 {zip_name} 中未找到目标 Excel")
                # 打印前 3 个解压出来的文件作为参考，看看路径错哪了
                sample_files = list(Path(extract_sub_dir).rglob("*"))[:3]
                print(f"     [提示] 目录内实际内容举例: {[f.name for f in sample_files]}")
        except Exception as e:
            print(f"  🔥 [错误] 处理 {zip_name} 时发生异常: {e}")
    dataWr = excel(output_file)
    dataWr.excel_write(
        title=['网元名称', '网元分组', '网元类型', '版本信息', '补丁信息', '评估场景', '网元IP', 'ESN号'], data=dataall,
        sheetname='巡检网元汇总')
    dataWr.save_file()
    shutil.rmtree(temp_extract_dir)  # 删除临时文件


def collect_and_split_zip():  # 提取文件并压缩分片
    # --- 配置区域 ---
    source_dir = '/Users/shadowx/Documents/招行/巡检/2026Q1/20260324'
    temp_extract_dir = os.path.expanduser('/Users/shadowx/Documents/招行/巡检/2026Q1/20260324/temp_extract')
    # 新增：用于存放准备压缩的文件的文件夹
    collect_dir = os.path.expanduser('/Users/shadowx/Documents/招行/巡检/2026Q1/20260324/collected_reports')
    # 最终压缩包名称（不带后缀）
    output_zip_name = "巡检数据分析汇总"
    # 分片大小
    split_size = "18m"
    target_file_name = "NetWork Healthy Check Report(Engineer).xlsx"

    # 1. 环境初始化
    for d in [temp_extract_dir, collect_dir]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)
    zip_files = [f for f in os.listdir(source_dir) if f.endswith('.zip')]
    if not zip_files:
        print("❓ 未发现源压缩包")
        return
    print(f"📂 开始提取文件到: {collect_dir}")

    # 2. 遍历并提取文件
    for zip_name in zip_files:
        zip_path = os.path.join(source_dir, zip_name)
        extract_sub_dir = os.path.join(temp_extract_dir, zip_name.replace('.zip', ''))
        try:
            # 使用系统命令或 zipfile 解压（这里为了简化路径直接解压）
            shutil.unpack_archive(zip_path, extract_sub_dir)
            # 模糊搜索目标文件
            found_files = list(Path(extract_sub_dir).rglob(f"**/{target_file_name}"))
            for i, file_path in enumerate(found_files):
                # 为了防止不同压缩包里的 Excel 文件名完全一样导致覆盖
                # 我们把原始压缩包的名字作为前缀
                new_name = f"{zip_name.replace('.zip', '')}_{i}_{target_file_name}"
                dest_path = os.path.join(collect_dir, new_name)
                shutil.copy2(file_path, dest_path)
                print(f"  ✅ 已提取: {new_name}")
        except Exception as e:
            print(f"  ❌ 处理 {zip_name} 失败: {e}")

    # 3. 分片压缩
    if not os.listdir(collect_dir):
        print("💨 没有提取到任何文件，停止压缩。")
        return
    print(f"\n📦 正在进行分片压缩 ({split_size})...")
    # 切换工作目录到采集文件夹，这样压缩包里不会包含长长的绝对路径
    os.chdir(collect_dir)
    # 构建 macOS 系统 zip 命令: zip -s 18m -r [输出文件名] [待压缩目录/文件]
    # 我们直接把当前目录下的所有文件压缩
    zip_cmd = ["zip", "-s", split_size, "-r", f"../{output_zip_name}.zip", "."]
    try:
        result = subprocess.run(zip_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            final_path = os.path.abspath(f"../{output_zip_name}.zip")
            print(f"✨ 分片压缩完成！")
            print(f"📄 主压缩包位置: {final_path}")
            print(f"💡 如果生成了多个文件，请查看该目录下的 .z01, .z02 等文件。")
        else:
            print(f"🔥 压缩失败: {result.stderr}")
    except Exception as e:
        print(f"🔥 调用系统压缩命令出错: {e}")

    # 4. 彻底清理临时解压目录
    shutil.rmtree(temp_extract_dir)
    # 如果你想保留提取出来的原始 Excel 文件夹，可以注释掉下面这行
    # shutil.rmtree(collect_dir)


def mergeOriginalData():  # 汇总原始表格数据
    # --- 配置区域 ---
    source_file = '/Users/shadowx/Documents/招行/巡检/2026Q1/巡检设备清单汇总20260318更新.xlsx'  # 原始文件
    data = []
    openExcel = excel(source_file)
    sheetnames = openExcel.excelReadCread()
    num = 0
    for sheetname in sheetnames:
        if sheetname == '汇总':
            continue
        print(f'正在处理sheet\'{sheetname}\'')
        num += 1
        res = openExcel.excelReadSheet(sheetnum=sheetname, column=4)
        data.extend(res)
    print(f'处理完成...共汇总{num}个sheet')
    openExcel.excelClose()
    excelObj = excel('data/巡检原始数据汇总')
    excelObj.excel_write(title=['登陆IP', '登陆用户名', 'AB角色', '备注'], data=data,sheetname='巡检原始数据')
    excelObj.save_file()


if __name__ == "__main__":
    # collect_and_split_zip()
    mergeOriginalData()
