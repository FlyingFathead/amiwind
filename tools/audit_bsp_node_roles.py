#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Count BSP29 world-render versus inline point-collision node residency.

Read-only hypothesis audit. It does not remove nodes, alter BSPs or claim that
the current loader has realized these savings. Reachability, not face count,
determines a node's role; zero-face world nodes must remain render-resident.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from player_hull import lumps


def audit(raw, *, mnode_bytes=40, hull0_node_bytes=8):
    data = lumps(raw)
    formats = {1: '<4fi', 5: '<i2h6h2H', 7: '<Hhihh4Bi',
               10: '<ii6h2H4B', 14: '<9f7i'}
    try:
        records = {i: list(struct.iter_unpack(fmt, data[i])) for i, fmt in formats.items()}
    except struct.error as exc:
        raise ValueError('Invalid BSP record length') from exc
    nodes, leaves, models = records[5], records[10], records[14]
    if not models or not nodes or not leaves:
        raise ValueError('Missing world model, nodes or leaves')
    if models[0][9] != 0:
        raise ValueError('Current renderer requires world root node zero')
    if mnode_bytes <= 0 or hull0_node_bytes <= 0:
        raise ValueError('Target record sizes must be positive')
    for node in nodes:
        if not 0 <= node[0] < len(records[1]):
            raise ValueError('Invalid node plane')
        if node[9]+node[10] > len(records[7]):
            raise ValueError('Invalid node face range')
        for child in node[1:3]:
            if child >= len(nodes) or child < -len(leaves):
                raise ValueError('Invalid node child or negative leaf index')
    # Validate every component, including orphans, before reporting a useful count.
    state = [0]*len(nodes)
    for root in range(len(nodes)):
        if state[root]:
            continue
        stack = [(root, False)]
        while stack:
            node_id, finish = stack.pop()
            if node_id < 0:
                continue
            if finish:
                state[node_id] = 2
                continue
            if state[node_id] == 1:
                raise ValueError('Cycle in BSP node graph')
            if state[node_id] == 2:
                continue
            state[node_id] = 1
            stack.append((node_id, True))
            stack.extend((child, False) for child in nodes[node_id][1:3] if child >= 0)
    def reachable(roots):
        found = set()
        todo = list(roots)
        while todo:
            node_id = todo.pop()
            if node_id < 0:
                if node_id < -len(leaves):
                    raise ValueError('Invalid model negative leaf root')
                continue
            if node_id >= len(nodes):
                raise ValueError('Invalid model node root')
            if node_id not in found:
                found.add(node_id)
                todo.extend(nodes[node_id][1:3])
        return found
    world = reachable([models[0][9]])
    inline = reachable(model[9] for model in models[1:])
    collision_only = inline-world
    orphan = set(range(len(nodes)))-world-inline
    eligible = {i for i in collision_only if nodes[i][10] == 0}
    faceful = collision_only-eligible
    prefix = world == set(range(len(world)))
    savings = len(eligible)*mnode_bytes
    return {'status': 'counting report; loader optimization not implemented',
            'sha256': hashlib.sha256(raw).hexdigest(),
            'nodes_total': len(nodes), 'world_render_nodes': len(world),
            'world_render_zero_face_nodes': sum(nodes[i][10] == 0 for i in world),
            'inline_point_nodes': len(inline), 'shared_world_inline_nodes': len(world & inline),
            'inline_only_nodes': len(collision_only), 'eligible_collision_only_zero_face_nodes': len(eligible),
            'inline_only_nodes_with_faces_require_review': len(faceful), 'unreferenced_nodes': len(orphan),
            'inline_models': len(models)-1, 'inline_negative_leaf_roots': sum(m[9] < 0 for m in models[1:]),
            'world_nodes_are_contiguous_prefix': prefix,
            'target_mnode_bytes': mnode_bytes, 'target_hull0_node_bytes': hull0_node_bytes,
            'current_expanded_node_bytes': len(nodes)*mnode_bytes,
            'current_hull0_node_bytes': len(nodes)*hull0_node_bytes,
            'avoidable_expanded_resident_bytes_before_bookkeeping': savings,
            'general_remap_int32_bytes': len(nodes)*4,
            'general_remap_and_traversal_int32_scratch_bytes': len(nodes)*8,
            'safe_prefix_candidate': prefix and not faceful and not orphan and not (world & inline),
            'constraints': ['All original hull0 nodes, child contents and model roots must remain valid.',
                            'World nodes/leaves/parent links and renderer/light/PVS consumers remain unchanged.',
                            'Current loader still expands every node; these bytes are not realized savings.',
                            'New load order and temporary classification memory require peak modeling.',
                            'Nonzero-face inline-only nodes and orphans are excluded from the conservative saving.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bsp', type=Path, nargs='+')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    reports = [{'path': str(path), **audit(path.read_bytes())} for path in args.bsp]
    text = json.dumps(reports, indent=2)+'\n'
    if args.out:
        args.out.write_text(text, encoding='utf-8')
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
