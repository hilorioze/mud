from mud.world import World, load_world

WORLD: World = load_world()


def test_rooms_and_exits_exist() -> None:
    assert WORLD.start in WORLD.rooms
    assert WORLD.goal.room in WORLD.rooms

    for room in WORLD.rooms.values():
        assert set(room.exits.values()) <= set(WORLD.rooms)
        assert set(room.locks) <= set(room.exits)


def test_items_exist_and_goal_items_can_be_carried() -> None:
    for room in WORLD.rooms.values():
        assert set(room.items) <= set(WORLD.items)
        assert {lock.item for lock in room.locks.values()} <= set(WORLD.items)

    for item in WORLD.goal.items:
        assert WORLD.items[item].fixed is None


def test_every_room_is_reachable_from_the_start() -> None:
    reached: set[str] = {WORLD.start}
    queue: list[str] = [WORLD.start]

    while queue:
        for target in WORLD.rooms[queue.pop()].exits.values():
            if target not in reached:
                reached.add(target)
                queue.append(target)

    assert reached == set(WORLD.rooms)


def test_item_words_are_unambiguous() -> None:
    words: list[str] = []
    for item_id, item in WORLD.items.items():
        words.extend([item_id, *item.aliases])

    assert len(words) == len(set(words))
