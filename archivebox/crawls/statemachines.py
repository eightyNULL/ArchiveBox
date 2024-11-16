__package__ = 'archivebox.crawls'

from statemachine import State, StateMachine

from crawls.models import Crawl

# State Machine Definitions
#################################################


class CrawlMachine(StateMachine, strict_states=True):
    """State machine for managing Crawl lifecycle."""
    
    model: Crawl
    
    # States
    queued = State(value=Crawl.StatusChoices.QUEUED, initial=True)
    started = State(value=Crawl.StatusChoices.STARTED)
    sealed = State(value=Crawl.StatusChoices.SEALED, final=True)
    
    # Tick Event
    tick = (
        queued.to.itself(unless='can_start') |
        queued.to(started, cond='can_start') |
        started.to.itself(unless='is_finished') |
        started.to(sealed, cond='is_finished')
    )
    
    def __init__(self, crawl, *args, **kwargs):
        self.crawl = crawl
        super().__init__(crawl, *args, **kwargs)
        
    def can_start(self) -> bool:
        return self.crawl.seed and self.crawl.seed.uri
        
    def is_finished(self) -> bool:
        if not self.crawl.snapshot_set.exists():
            return False
        if self.crawl.pending_snapshots().exists():
            return False
        if self.crawl.pending_archiveresults().exists():
            return False
        return True
        
    # def before_transition(self, event, state):
    #     print(f"Before '{event}', on the '{state.id}' state.")
    #     return "before_transition_return"

    @started.enter
    def on_started(self):
        print(f'CrawlMachine[{self.crawl.ABID}].on_started(): crawl.create_root_snapshot() + crawl.bump_retry_at(+10s)')
        self.crawl.create_root_snapshot()
        self.crawl.bump_retry_at(seconds=10)
        self.crawl.save()

    @sealed.enter        
    def on_sealed(self):
        print(f'CrawlMachine[{self.crawl.ABID}].on_sealed(): crawl.retry_at=None')
        self.crawl.retry_at = None
        self.crawl.save()

