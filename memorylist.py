#!/usr/bin/env python3

from collections.abc import MutableSequence


class MemoryList(MutableSequence):
    def __init__(self, capacity, data=None):
        """Initialize the class"""
        super(MemoryList, self).__init__()
        self._capacity = capacity
        if (data is not None):
            self._list = list(data)
        else:
            self._list = list()

    def __repr__(self):
        return "<{0} {1}, capacity {2}>".format(self.__class__.__name__, self._list, self._capacity)

    def __len__(self):
        """List length"""
        return len(self._list)

    def capacity(self):
        return self._capacity

    def __getitem__(self, ii):
        """Get a list item"""
        return self._list[ii]

    def __delitem__(self, ii):
        """Delete an item"""
        del self._list[ii]

    def __setitem__(self, ii, val):
        self._list[ii] = val

    def __str__(self):
        return str(self._list)

    def __contains__(self, val):
        return val in self._list

    def __iter__(self):
        return self._list.__iter__()

    def insert(self, ii, val):
        self._list.insert(ii, val)

    def append(self, val):
        if val in self._list:
            self._list.remove(val)

        self._list.append(val)
        if len(self._list) >= self._capacity:
            x = self._list[0]
            del self._list[0]
            return x
        else:
            return None

    def get_next(self, cond):
        val = next((v for v in self._list if cond(v)), None)
        if val is not None:
            self._list.remove(val)
            self._list.append(val)
        return val

    def remove(self, val):
        self._list.remove(val)
