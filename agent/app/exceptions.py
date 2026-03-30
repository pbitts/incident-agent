class PendingApprovalException(Exception):
    def __init__(self, thread_id: str, pending_actions: list):
        self.thread_id = thread_id
        self.pending_actions = pending_actions
        super().__init__(f"Pending approval for thread {thread_id}")