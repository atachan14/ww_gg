"""Explicit policy/value dependencies; recording never changes a policy."""
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class Dependency:
    kind: str
    context: tuple


class DependencyCycle(Exception):
    def __init__(self,path):self.path=path


class DependencyGraph:
    def __init__(self):
        self.edges={};self.stack=[];self.completed=set()

    def request(self,node):
        self.edges.setdefault(node,set())
        if self.stack:self.edges[self.stack[-1]].add(node)
        return node

    @contextmanager
    def evaluating(self,node,*,allow_reentry=False):
        self.request(node)
        if node in self.stack and not allow_reentry:
            start=self.stack.index(node)
            raise DependencyCycle(tuple(self.stack[start:]+[node]))
        self.stack.append(node)
        try:yield
        except BaseException:raise
        else:self.completed.add(node)
        finally:
            assert self.stack.pop()==node

    def components(self):
        """Strongly connected components, including recorded cached requests."""
        indices={};low={};active=[];on_stack=set();result=[]
        def visit(node):
            indices[node]=low[node]=len(indices);active.append(node);on_stack.add(node)
            for child in self.edges[node]:
                if child not in indices:visit(child);low[node]=min(low[node],low[child])
                elif child in on_stack:low[node]=min(low[node],indices[child])
            if low[node]==indices[node]:
                group=[]
                while True:
                    child=active.pop();on_stack.remove(child);group.append(child)
                    if child==node:break
                result.append(tuple(group))
        for node in self.edges:
            if node not in indices:visit(node)
        return tuple(result)

    def cycles(self):
        return tuple(c for c in self.components() if len(c)>1 or c[0] in self.edges[c[0]])
