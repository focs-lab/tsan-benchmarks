from util import Context


class Builder:
    ctx: Context

    def __init__(self, ctx: Context):
        self.ctx = ctx

    def build_all(self):
        self.sync_and_build_llvm()
        self.rebuild_v8()

    def maybe_clone_llvm(self):
        # TODO(dwslim): implement
        pass

    def sync_and_build_llvm(self):
        self.maybe_clone_llvm()
        self.sync_llvm()
        self.build_llvm()

    def sync_llvm(self):
        self.ctx.logger.info(f"Syncing LLVM")
        # TODO(dwslim): implement

    def build_llvm(self):
        self.ctx.logger.info(f"Building LLVM")
        # TODO(dwslim): implement

    def maybe_clone_v8(self):
        # TODO(dwslim): implement
        pass

    def rebuild_v8(self):
        self.maybe_clone_v8()
        self.ctx.logger.info(f"Building V8")
        # TODO(dwslim): implement
