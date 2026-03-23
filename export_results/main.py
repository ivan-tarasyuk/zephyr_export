import argparse

from export_results.exporter import ResultExporter


async def main():
    parser = argparse.ArgumentParser(description='Parses test execution results and updates Zephyr test cases')
    parser.add_argument('-s', '--send_status', action='store_true', help='send execution status (disabled by default)')
    args = parser.parse_args()
    exported_count = 0
    try:
        async with ResultExporter(args.send_status) as result_exporter:
            exported_count = await result_exporter.run()
    except Exception as e:
        print(e)
    print(f'[DONE ] Script has been completed')
    if exported_count:
        print(f'[DONE ] Exported {exported_count} test execution result(s)')
    else:
        print('[DONE ] No test execution results have been exported')
