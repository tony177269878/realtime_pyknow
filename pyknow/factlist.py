"""
``fact-list`` implementation from CLIPS.

See `Making a List <http://clipsrules.sourceforge.net/docume\
    ntation/v624/ug.htm#_Toc412126071>`_  section on the user guide. \
Also see `retrieving the fact-list \
  <http://clipsrules.sourceforge.net/d\
          ocumentation/v624/bpg.htm#_Toc11859921>`_ on the clips\
          programming manual
"""

from collections import OrderedDict, Counter
from pyknow.fact import Fact
from pyknow import watchers


class FactList(OrderedDict):
    """
    Contains a list of facts (``asserted`` data).

    In clips, there is the concept of "modules"
    (:obj:`pyknow.engine.KnowledgeEngine`), wich have their own
    :obj:`pyknow.factlist.FactList` and :obj:`pyknow.agenda.Agenda`

    A factlist acts as both the module's factlist and a ``fact-set``
    yet currently most methods from a ``fact-set`` are not yet
    implemented
    """

    def __init__(self):
        super().__init__()
        self.last_index = 0
        self.reference_counter = Counter()
        self.added = list()
        self.removed = list()
        self.duplication = False

        self.fact_id_2_idx_map = {}

    def __str__(self):  # pragma: no cover
        return "\n".join(
            "%s: %r" % (fact, fact)
            for idx, fact in self.items())

    @staticmethod
    def _get_fact_id(fact):
        if 'level' in fact.keys() and 'id' in fact.keys():
            return f"{fact['level']}_{fact['id']}"
        else:
            return frozenset([fact.__class__]
                             + [(k, v)
                                for k, v in fact.items()
                                if not fact.is_special(k)])

    def get_fact_from_partial(self,fact):
        if 'level' in fact.keys() and 'id' in fact.keys():
            key = f"{fact['level']}_{fact['id']}"
            if key in self.fact_id_2_idx_map.keys() and self.fact_id_2_idx_map[key] in self.keys():
                return self[self.fact_id_2_idx_map[key]]
            else:
                return None
        else:
            return None

    def declare(self, fact):
        """
        Assert (in clips terminology) a fact.

        This keeps insertion order.

        .. warning:: This will reject any object that not descend
                     from the Fact class.

        :param fact: The fact to declare, **must** be derived from
                     :obj:`pyknow.fact.Fact`.
        :return: (int) The index of the fact in the list.
        :throws ValueError: If the fact providen is not a Fact object

        """

        if not isinstance(fact, Fact):
            raise ValueError('The fact must descend the Fact class.')

        # Validate fact, will raise on validation error.
        fact.validate()

        fact_id = self._get_fact_id(fact)

        if self.duplication or fact_id not in self.reference_counter:
            # Assign the ID to the fact
            idx = self.last_index
            fact.__factid__ = idx
            self.fact_id_2_idx_map[fact_id] = idx

            # Insert the fact in the factlist
            self[idx] = fact

            self.last_index += 1

            self.added.append(fact)
            self.reference_counter[fact_id] += 1

            watchers.FACTS.info(" ==> %s: %r", fact, fact)
            return fact
        elif fact_id in self.reference_counter:
            old_fact = self[self.fact_id_2_idx_map[fact_id]]
            if 'level' in old_fact.keys() and 'id' in old_fact.keys():
                self.removed.append(old_fact)

                del self[self.fact_id_2_idx_map[fact_id]]
                del self.fact_id_2_idx_map[fact_id]

                idx = self.last_index
                fact.__factid__ = idx
                self.fact_id_2_idx_map[fact_id] = idx

                # Insert the fact in the factlist
                self[idx] = fact

                self.last_index += 1

                self.added.append(fact)

                watchers.FACTS.info(" ==> %s: %r", fact, fact)
                return fact
            else:
                return None
        else:
            return None

    def retract(self, idx_or_fact):
        """
        Retract a previously asserted fact.

        See `"Retract that fact" in Clips User Guide
        <http://clipsrules.sourceforge.net/doc\
                umentation/v624/ug.htm#_Toc412126077>`_.

        :param idx: The index of the fact to retract in the factlist
        :return: (int) The retracted fact's index
        :throws IndexError: If the fact's index providen does not exist
        """

        if isinstance(idx_or_fact, int):
            idx = idx_or_fact
        else:
            idx = idx_or_fact.__factid__

        if idx not in self:
            raise IndexError('Fact not found.')

        fact = self[idx]

        # Decrement value reference counter
        fact_id = self._get_fact_id(fact)
        self.reference_counter[fact_id] -= 1
        if self.reference_counter[fact_id] == 0:
            self.reference_counter.pop(fact_id)

        watchers.FACTS.info(" <== %s: %r", fact, fact)
        self.removed.append(fact)

        del self[idx]
        del self.fact_id_2_idx_map[fact_id]

        return idx

    @property
    def changes(self):
        """
        Return a tuple with the removed and added facts since last run.
        """
        try:
            return self.values(),self.removed
            # return self.added, self.removed
        finally:
            self.added = list()
            self.removed = list()
