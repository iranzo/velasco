#!/usr/bin/env python3

from collections.abc import Sequence


class MemoryList(Sequence):
    """Special "memory list" class that:
       - Whenever an item is added that was already in the list,
         it gets moved to the back instead
       - Whenever an item is looked for, it gets moved to the
         back
       - If a new item is added that goes over a given capacity
         limit, the item at the front (oldest accessed item)
         is removed (and returned)"""

    def __init__(self, capacity, data=None):
        super(MemoryList, self).__init__()
        self._capacity = capacity
        if (data is not None):
            self._list = list(data)
        else:
            self._list = list()

    def __repr__(self):
        return "<{0} {1}, capacity {2}>".format(self.__class__.__name__, self._list, self._capacity)

    def __str__(self):
        return "{0}, {1}/{2}".format(self._list, len(self._list), self._capacity)

    def __len__(self):
        return len(self._list)

    def capacity(self):
        return self._capacity

    def __getitem__(self, ii):
        return self._list[ii]

    def __contains__(self, val):
        return val in self._list

    def __iter__(self):
        return self._list.__iter__()

    def add(self, val):
        if val in self._list:
            self._list.remove(val)

        self._list.append(val)
        if len(self._list) >= self._capacity:
            x = self._list[0]
            del self._list[0]
            return x
        else:
            return None

    def search(self, cond, *args, **kwargs):
        val = next((v for v in self._list if cond(v)), *args, **kwargs)
        if val is not None:
            self._list.remove(val)
            self._list.append(val)
        return val

    def remove(self, val):
        self._list.remove(val)
