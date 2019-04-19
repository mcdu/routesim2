from simulator.node import Node
import json, math

class Link_State_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.link_states = dict()
        self.forwarding_table = dict()

    def __str__(self):
        return json.dumps({'id': self.id, 'link_states': self.link_states})

    def link_has_been_updated(self, neighbor, latency):

        if neighbor not in self.neighbors:
            self.neighbors.append(neighbor)
        elif latency == -1 and neighbor in self.neighbors:
            self.neighbors.remove(neighbor)

        link = frozenset((self.id, neighbor))

        # Update my link state
        if link in self.link_states:
            seq_num = self.link_states[link][1] + 1
        else:
            seq_num = 0
        self.link_states[link] = (latency, seq_num)

        # Flood updated link state
        self.flood_ls(link)

        # If neighbor is new, update them with all my other, prior link states
        if seq_num == 0:
            self.update_neighbor(neighbor)

        # Run Dijkstra using new link states to update my forwarding_table
        self.update_forwarding_table()

    def process_incoming_routing_message(self, m):
        link_tuple, latency, seq_num, sender = json.loads(m)
        link = frozenset(link_tuple)

        # If message is old, send back the newer link state, and do nothing else
        #TODO optimize?
        if link in self.link_states:
            if seq_num <= self.link_states[link][1]:
                if seq_num < self.link_states[link][1]:
                    self.send_ls_to(link, sender)
                return

        # Update my link state
        self.link_states[link] = (latency, seq_num)

        # Flood updated link state
        self.flood_ls(link)

        # Run Dijkstra using new link statesto update my forwarding_table
        self.update_forwarding_table()

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        #self.update_forwarding_table(destination)
        if destination in self.forwarding_table:
            return self.forwarding_table[destination]
        else:
            return -1

    # Helper functions

    def update_forwarding_table(self):
    #def update_forwarding_table(self, destination):
        done_nodes = set([self.id])

        all_nodes = set()
        for link in self.link_states:
            all_nodes.update(link)

        dv = {}
        pred = {}
        for n in all_nodes:
            if n in self.neighbors:
                dv[n] = self.link_states[frozenset((self.id,n))][0]
                pred[n] = self.id
            else:
                dv[n] = math.inf

        while done_nodes != all_nodes:
            nodes_to_do = all_nodes.difference(done_nodes)
            next_cheapest_node = list(nodes_to_do)[0]
            for ntd in nodes_to_do:
                if dv[ntd] < dv[next_cheapest_node]:
                    next_cheapest_node = ntd
            done_nodes.add(next_cheapest_node)

            for ncn_neighbor in nodes_to_do:
                cl = frozenset((ncn_neighbor, next_cheapest_node))
                if cl in self.link_states:
                    maybe_better_cost = dv[next_cheapest_node] + self.link_states[cl][0]
                    if maybe_better_cost < dv[ncn_neighbor]:
                        dv[ncn_neighbor] = maybe_better_cost
                        pred[ncn_neighbor] = next_cheapest_node

        # trace back path from dest
        for destination in all_nodes:
            if destination != self.id and destination not in pred:
                self.forwarding_table[destination] = -1
            elif destination != self.id:
                p = destination
                while pred[p] != self.id:
                    p = pred[p]
                self.forwarding_table[destination] = p

    def make_ls_message(self, link):
        latency, seq_num = self.link_states[link]
        return json.dumps((tuple(link), latency, seq_num, self.id))

    def flood_ls(self, link):
        ls = self.make_ls_message(link)
        self.send_to_neighbors(ls)

    def send_ls_to(self, link, neighbor):
        ls = self.make_ls_message(link)
        self.send_to_neighbor(neighbor, ls)

    def update_neighbor(self, neighbor):
        link_with_neighbor = frozenset((self.id, neighbor))
        for link in self.link_states:
            if link != link_with_neighbor:
                self.send_ls_to(link, neighbor)
