from simulator.node import Node
import math, json

class Distance_Vector_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.logging.debug("new node %d" % self.id)        
        self.previously_seen = dict()
        self.seq_num = 0
        self.neighbor_link_cost = dict()
        self.routing_table = {
                               id: {id: (0, set())}
                             }
        self.forwarding_table = dict()

    def __str__(self):
        return json.dumps({'id': self.id, 'routing_table': self.routing_table})

    def link_has_been_updated(self, neighbor, latency):
        if latency == -1: # link deleted
            self.neighbors.remove(neighbor)
            del self.neighbor_link_cost[neighbor]
        else:
            if neighbor not in self.neighbors:
                self.neighbors.append(neighbor)
                # for now i won't chcek if needs adding to new_nodes bc message should eventually arrive
                #if neighbor not in self.routing_table[self.id]:
                #    self.routing_table[self.id][neighbor] = (math.inf, set())
            self.neighbor_link_cost[neighbor] = latency

        if self.update_dv(True):
            self.send_dv_to_neighbors()

    def process_incoming_routing_message(self, m):
        dv_message = json.loads(m)
        sender = dv_message[0]
        sender_dv = dv_message[1]
        seq_num = dv_message[2]

        #adjust
        if sender in self.previously_seen:
            if self.previously_seen[sender] >= seq_num:
                return
        self.previously_seen[sender] = seq_num

        parsed_sender_dv = dict()
        for str_node, val in sender_dv.items():
            parsed_sender_dv[int(str_node)] = (val[0], set(val[1])) # may need to unstring tuple val

        dv_updated = False
        for node in parsed_sender_dv:
            # if find out about new node in dest field of recveied dv, change our dv entry to node to inf
            if node not in self.routing_table[self.id]:
                self.routing_table[self.id][node] = (math.inf, set())
                dv_updated = True
        self.routing_table[sender] = parsed_sender_dv

        if self.update_dv(dv_updated):
            self.send_dv_to_neighbors()

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        if destination in self.forwarding_table:
            return self.forwarding_table[destination]
        else:
            return -1


    # Helper functions

    def make_dv_message(self):
        temp_dv = dict()
        for key, val in self.routing_table[self.id].items():
            temp_dv[key] = (val[0], list(val[1]))
        dv_message = (self.id, temp_dv, self.seq_num)
        return json.dumps(dv_message)

    def update_dv(self, dv_updated):
        # loop through known nodes
        for node, cost_and_path_to_node in self.routing_table[self.id].items():
            if node != self.id:
                cost_to_node = cost_and_path_to_node[0]
                path_to_node = cost_and_path_to_node[1]
                new_cost_to_node = math.inf
                next_hop_to_node = -1
                for neighbor in self.neighbors:
                    if neighbor in self.routing_table:
                        neighbor_dv = self.routing_table[neighbor]
                        if node in neighbor_dv and self.id not in neighbor_dv[node][1]: #if second cond failed then we wont msg neighbors about new inf node
                            cost_via_neighbor_path = self.neighbor_link_cost[neighbor] + neighbor_dv[node][0]
                            if cost_via_neighbor_path < new_cost_to_node:
                                new_cost_to_node = cost_via_neighbor_path
                                next_hop_to_node = neighbor

                # update dv if best path length to node has changed
                if cost_to_node != new_cost_to_node:
                    new_path_to_node = set()
                    if next_hop_to_node != -1:
                        new_path_to_node = self.routing_table[next_hop_to_node][node][1]
                        new_path_to_node.add(next_hop_to_node)
                    self.routing_table[self.id][node] = (new_cost_to_node, new_path_to_node)
                    dv_updated = True
                    self.forwarding_table[node] = next_hop_to_node # may or may not have also changed
        # return bool indicating if dv was updated at all
        return dv_updated

    def send_dv_to_neighbors(self):
        dv = self.make_dv_message()
        self.seq_num += 1
        self.send_to_neighbors(dv)
