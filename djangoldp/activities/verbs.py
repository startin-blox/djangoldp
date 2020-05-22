from copy import copy

from djangoldp.activities import errors
from djangoldp.activities.objects import ALLOWED_TYPES, Object, Actor


class Activity(Object):
    attributes = Object.attributes + ["actor", "object"]
    type = "Activity"

    def get_audience(self):
        audience = []
        for attr in ["to", "bto", "cc", "bcc", "audience"]:
            value = getattr(self, attr, None)
            if not value:
                continue

            if isinstance(value, str):
                value = [value]
            audience += value
        return set(audience)

    def strip_audience(self):
        new = copy(self)
        if getattr(new, "bto", None):
            delattr(new, "bto")
        if getattr(new, "bcc", None):
            delattr(new, "bcc")
        return new

    def validate(self):
        pass


class Add(Activity):
    type = "Add"
    attributes = Activity.attributes + ["target"]

    def validate(self):
        msg = None
        if not getattr(self, "actor", None):
            msg = "Invalid activity, actor is missing"
        elif not getattr(self, "object", None):
            msg = "Invalid activity, object is missing"
        elif not getattr(self, "target", None):
            msg = "Invalid activity, target is missing"
        elif not isinstance(self.actor, Actor) and not isinstance(self.actor, str):
            msg = "Invalid actor type, must be an Actor or a string"
        elif not isinstance(self.object, dict):
            msg = "Invalid object type, must be a dict"
        elif not isinstance(self.target, dict):
            msg = "Invalid target type, must be a dict"

        if msg:
            raise errors.ActivityStreamValidationError(msg)


class Remove(Activity):
    type = "Remove"
    attributes = Activity.attributes + ["target", "origin"]

    def validate(self):
        msg = None
        if not getattr(self, "actor", None):
            msg = "Invalid activity, actor is missing"
        elif not getattr(self, "object", None):
            msg = "Invalid activity, object is missing"
        elif not getattr(self, "target", None) and not getattr(self, "origin", None):
            msg = "Invalid activity, no target or origin given"
        elif not isinstance(self.actor, Actor) and not isinstance(self.actor, str):
            msg = "Invalid actor type, must be an Actor or a string"
        elif not isinstance(self.object, dict):
            msg = "Invalid object type, must be a dict"

        if getattr(self, "target", None) is not None:
            if not isinstance(self.target, dict):
                msg = "Invalid target type, must be a dict"
        if getattr(self, "origin", None) is not None:
            if not isinstance(self.origin, dict):
                msg = "Invalid origin type, must be a dict"

        if msg:
            raise errors.ActivityStreamValidationError(msg)


class Create(Activity):
    type = "Create"

    def validate(self):
        msg = None

        if not getattr(self, "actor", None):
            msg = "Invalid activity, actor is missing"
        elif not getattr(self, "object", None):
            msg = "Invalid activity, object is missing"
        elif not isinstance(self.actor, Actor) and not isinstance(self.actor, str):
            msg = "Invalid actor type, must be an Actor or a string"
        elif not isinstance(self.object, dict):
            msg = "Invalid object type, must be a dict"

        if msg:
            raise errors.ActivityStreamValidationError(msg)


class Update(Create):
    type = "Update"


class Delete(Activity):
    type = "Delete"
    attributes = Activity.attributes + ["origin"]

    def validate(self):
        msg = None
        if not getattr(self, "actor", None):
            msg = "Invalid activity, actor is missing"
        elif not getattr(self, "object", None):
            msg = "Invalid activity, object is missing"
        elif not isinstance(self.actor, Actor) and not isinstance(self.actor, str):
            msg = "Invalid actor type, must be an Actor or a string"
        elif not isinstance(self.object, dict):
            msg = "Invalid object type, must be a dict"

        if msg:
            raise errors.ActivityStreamValidationError(msg)


class Follow(Activity):
    type = "Follow"

    def validate(self):
        msg = None

        if not getattr(self, "actor", None):
            msg = "Invalid activity, actor is missing"
        elif not getattr(self, "object", None):
            msg = "Invalid activity, object is missing"
        elif not isinstance(self.actor, Actor) and not isinstance(self.actor, str):
            msg = "Invalid actor type, must be an Actor or a string"
        elif isinstance(self.actor, Actor) and (self.actor.inbox is None and self.actor.id is None):
            msg = "Must pass inbox or id with the actor to follow"
        elif not isinstance(self.object, dict):
            msg = "Invalid object type, must be a dict"

        if msg:
            raise errors.ActivityStreamValidationError(msg)


ALLOWED_TYPES.update({
    "Activity": Activity,
    "Add": Add,
    "Remove": Remove,
    "Create": Create,
    "Update": Update,
    "Delete": Delete,
    "Follow": Follow
})
