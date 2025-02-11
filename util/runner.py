from util import Context


class Runner:
    ctx: Context

    def __init__(self, ctx: Context):
        self.ctx = ctx

    def run_all(self):
        self.run_v8_benchmarks()
        self.run_mysql_benchmarks()
        self.export_results()

    def run_v8_benchmarks(self):
        self.ctx.logger.info(f"Running V8 benchmarks")
        # TODO(dwslim): implement

    def run_mysql_benchmarks(self):
        self.ctx.logger.info(f"Running MySQL benchmarks")
        # TODO(dwslim): implement
        
    def export_results(self):
        self.ctx.logger.info("Exporting results to results/ directory")
        # TODO(dwslim): implement
