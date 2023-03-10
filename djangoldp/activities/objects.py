import json
import requests
from djangoldp.activities import errors


class Object(object):
    attributes = ["type", "id", "name", "to"]
    type = "Object"

    @classmethod
    def from_json(cls, json):
        return Object(**json)

    def __init__(self, obj=None, **kwargs):
        if obj:
            self.__init__(**obj.to_activitystream())
        for key in self.attributes:
            value = kwargs.get(key)
            if value is None:
                continue

            if isinstance(value, dict) and value.get("type"):
                value = as_activitystream(value)
            self.__setattr__(key, value)

    def __str__(self):
        content = json.dumps(self, default=encode_activitystream)
        return "<{type}: {content}>".format(type=self.type, content=content)

    def to_json(self, context=False):
        '''
        converts Object to json
        context parameter indicates whether @context should be added to the object (for JSON-LD parsing)
        '''
        values = {}
        for attribute in self.attributes:
            value = getattr(self, attribute, None)
            if value is None:
                continue
            if isinstance(value, Object):
                value = value.to_json()
            # if getattr(value, "__iter__", None):
            #     value = [item.to_json() for item in value]
            values[attribute] = value
        to = values.get("to")
        if isinstance(to, str):
            values["to"] = [to]
        elif getattr(to, "__iter__", None):
            values["to"] = []
            for item in to:
                if isinstance(item, str):
                    values["to"].append(item)
                if isinstance(item, Object):
                    values["to"].append(item.id)

        if context:
            values["@context"] = "https://www.w3.org/ns/activitystreams"
        return values

    def to_activitystream(self):
        return self


class Actor(Object):
    attributes = Object.attributes + [
        "target",
        "publicKey",
        "preferredUsername",
        "following",
        "followers",
        "outbox",
        "inbox",
    ]
    type = "Actor"

    def send(self, activity):
        res = requests.post(self.inbox, json=activity.to_json(context=True))
        if res.status_code != 200:
            raise Exception


class Person(Actor):
    type = "Person"


class Service(Actor):
    type = "Service"


class Group(Actor):
    type = "Group"


class Collection(Object):
    attributes = Object.attributes + ["items", "totalItems"]
    type = "Collection"

    def __init__(self, iterable=None, **kwargs):
        self._items = []

        Object.__init__(self, **kwargs)
        if iterable is None:
            return

        self.items = iterable

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, iterable):
        for item in iterable:
            if isinstance(item, Object):
                self._items.append(item)
            elif isinstance(item, str):
                self._items.append(item)
            elif getattr(item, "to_activitystream", None):
                item = as_activitystream(item.to_activitystream())
                self._items.append(item)
            else:
                raise Exception("invalid ActivityStream object: {item}".format(item=item))

    def to_json(self, **kwargs):
        json = Object.to_json(self, **kwargs)
        items = [item.to_json() if isinstance(item, Object) else item
                 for item in self.items]
        json.update({
            "items": items
        })
        return json


class OrderedCollection(Collection):
    attributes = Object.attributes + ["orderedItems", "totalItems"]
    type = "OrderedCollection"

    @property
    def totalItems(self):
        return len(self.items)

    @totalItems.setter
    def totalItems(self, value):
        pass

    @property
    def orderedItems(self):
        return self.items

    @orderedItems.setter
    def orderedItems(self, iterable):
        self.items = iterable

    def to_json(self, **kwargs):
        json = Collection.to_json(self, **kwargs)
        json["orderedItems"] = json["items"]
        del json["items"]
        return json


class Link(Object):
    type = 'Link'
    attributes = ['link']

    def to_json(self, **kwargs):
        return self.link


#########
# Utils #
#########

ALLOWED_TYPES = {
    "Object": Object,
    "Actor": Actor,
    "Service": Service,
    "Person": Person,
    "Link": Link,
    "Collection": Collection,
    "OrderedCollection": OrderedCollection
}


def as_activitystream(obj):
    type = obj.get("type")

    if type:
        if type in ALLOWED_TYPES:
            obj = ALLOWED_TYPES[type](**obj)
            return obj

        raise errors.ActivityStreamDecodeError("Invalid Type {0}".format(type))

    return obj


def encode_activitystream(obj):
    if isinstance(obj, Object):
        return obj.to_json()
    raise errors.ActivityStreamTypeError("Unknown ActivityStream Type")
