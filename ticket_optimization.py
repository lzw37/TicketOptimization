# -*- coding: utf-8 -*-

import csv
from gurobipy import *
import matplotlib.pyplot as plt


class TicketPrototype:
    pass


class Ticket:
    def __init__(self):
        self.start_time = dict()


class Validation:
    pass


class Trip:
    pass


trip_dict = dict()
ticket_prototype_dict = dict()
ticket_dict = dict()

time_horizon_length = 250


def presolve():
    for ticket_prototype in ticket_prototype_dict.values():
        ticket_dict[ticket_prototype.id] = dict()
        for i in range(0, ticket_prototype.stock_number):
            ticket = Ticket()
            ticket.prototype = ticket_prototype
            ticket.sequence = i
            ticket_dict[ticket_prototype.id][i] = ticket


def solve():
    m = Model('Ticket_Optimization')

    # Variables
    # variable d: the departure time cumulative flow for a trip
    for trip in trip_dict.values():
        for t in range(0, time_horizon_length):
            m.addVar(0.0, 1.0, 0.0, GRB.BINARY, 'd_' + trip.id + '_' + str(t))

    # variable theta: the on board binary indicator
    for trip in trip_dict.values():
        for t in range(0, time_horizon_length):
            m.addVar(0.0, 1.0, 0.0, GRB.BINARY, 'theta_' + trip.id + '_' + str(t))

    # variable x: the selection of a ticket instance
    for ticket_proto in ticket_dict:
        for ticket in ticket_dict[ticket_proto].values():
            m.addVar(0.0, 1.0, ticket_prototype_dict[ticket_proto].price, GRB.BINARY,
                     'x_' + ticket_proto + '_' + str(ticket.sequence))

    # variable s: the start time cumulative flow for a validation
    for ticket_proto in ticket_dict:
        for ticket in ticket_dict[ticket_proto].values():
            for i in range(0, ticket_prototype_dict[ticket_proto].validation_number):
                for t in range(0, time_horizon_length):
                    m.addVar(0.0, 1.0, 0.0, GRB.BINARY,
                             's_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t))

    # variable delta: the valid condition indicator
    for ticket_proto in ticket_dict:
        for ticket in ticket_dict[ticket_proto].values():
            for i in range(0, ticket_prototype_dict[ticket_proto].validation_number):
                for t in range(0, time_horizon_length):
                    m.addVar(0.0, 1.0, 0.0, GRB.BINARY,
                             'delta_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t))

    m.update()

    # constraint 1: cumulative flow for variable d
    for trip in trip_dict.values():
        for t in range(0, time_horizon_length - 1):
            d_t = m.getVarByName('d_' + trip.id + '_' + str(t))
            d_t_plus_1 = m.getVarByName('d_' + trip.id + '_' + str(t + 1))
            m.addConstr(d_t <= d_t_plus_1, "ct1_" + trip.id + '_' + str(t))

    # constraint 2: cumulative flow for variable s
    for ticket_proto in ticket_dict:
        for ticket in ticket_dict[ticket_proto].values():
            for i in range(0, ticket_prototype_dict[ticket_proto].validation_number):
                for t in range(0, time_horizon_length - 1):
                    s_t = m.getVarByName('s_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t))
                    s_t_plus_1 = m.getVarByName(
                        's_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t + 1))
                    m.addConstr(s_t <= s_t_plus_1,
                                "ct3_" + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t))

    # constraint 3: indicator theta
    for trip in trip_dict.values():
        for t in range(0, time_horizon_length):
            theta = m.getVarByName('theta_' + trip.id + '_' + str(t))
            d = m.getVarByName('d_' + trip.id + '_' + str(t))
            if t - trip.duration < 0:
                d_p = 0
            else:
                d_p = m.getVarByName('d_' + trip.id + '_' + str(t - trip.duration))
            m.addConstr(theta == d - d_p, "ct2_" + trip.id + '_' + str(t))

    # constraint 4: indicator delta
    for ticket_proto in ticket_dict:
        for ticket in ticket_dict[ticket_proto].values():
            for i in range(0, ticket_prototype_dict[ticket_proto].validation_number):
                for t in range(0, time_horizon_length):
                    if t - ticket_prototype_dict[ticket_proto].duration_per_validation < 0:
                        s_p = 0
                    else:
                        s_p = m.getVarByName(
                            's_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(
                                t - ticket_prototype_dict[ticket_proto].duration_per_validation))
                    delta = m.getVarByName(
                        'delta_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t))
                    s = m.getVarByName('s_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t))
                    m.addConstr(delta == s - s_p,
                                "ct4_" + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t))

    # constraint 5: departure time windows
    for trip in trip_dict.values():
        for t in range(0, time_horizon_length):
            d_t = m.getVarByName('d_' + trip.id + '_' + str(t))
            if t < trip.earliest_departure_time:
                m.addConstr(d_t == 0, 'ct5_' + trip.id + '_' + str(t))
            else:
                if t > trip.latest_departure_time:
                    m.addConstr(d_t == 1, 'ct5_' + trip.id + '_' + str(t))

    # constraint 6: ticket selection - validation mapping
    for ticket_proto in ticket_dict:
        for ticket in ticket_dict[ticket_proto].values():
            x = m.getVarByName('x_' + ticket_proto + '_' + str(ticket.sequence))
            for i in range(0, ticket_prototype_dict[ticket_proto].validation_number):
                s = m.getVarByName('s_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(
                    time_horizon_length - 1))
                m.addConstr(x - s == 0, 'ct6_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(
                    time_horizon_length - 1))

                s_0 = m.getVarByName('s_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(0))
                m.addConstr(s_0 == 0, 'ct62_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(0))

    # constraint 7: trip covering
    for t in range(0, time_horizon_length):
        for trip in trip_dict.values():
            theta = m.getVarByName('theta_' + trip.id + '_' + str(t))

            supply_sum = 0
            for ticket_proto in ticket_dict:
                for ticket in ticket_dict[ticket_proto].values():
                    for i in range(0, ticket_prototype_dict[ticket_proto].validation_number):
                        delta = m.getVarByName(
                            'delta_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t))
                        supply_sum += delta

            m.addConstr(supply_sum >= theta, 'ct7_' + trip.id + '_' + str(t))

    m.write('model.lp')
    m.optimize()

    if m.status == GRB.OPTIMAL:
        m.write('solution.sol')
        output_solution(m)
        obj_value = m.objval
        print('Objective Value：' + str(obj_value))
        plot()
    else:
        print('No feasible solution!!!')


def read_trip_data():
    csv_file = open('plan.csv', 'r')
    reader = csv.DictReader(csv_file)
    for item in reader:
        trip = Trip()
        trip.id = item['trip_id']
        trip.earliest_departure_time = int(item['earliest_departure_time'])
        trip.latest_departure_time = int(item['latest_departure_time'])
        trip.duration = int(item['duration'])
        trip_dict[trip.id] = trip
    csv_file.close()


def read_ticket_data():
    csv_file = open('ticket.csv', 'r')
    reader = csv.DictReader(csv_file)
    for item in reader:
        ticket = TicketPrototype()
        ticket.id = item['ticket_id']
        ticket.type = item['ticket_type']
        ticket.validation_number = int(item['validation_number'])
        ticket.duration_per_validation = int(item['duration_per_validation'])
        ticket.price = float(item['price'])
        ticket.stock_number = int(item['stock_number'])
        ticket_prototype_dict[ticket.id] = ticket
    csv_file.close()


def output_solution(m):
    # output trip departure time
    for trip in trip_dict.values():
        for t in range(0, time_horizon_length - 1):
            d = m.getVarByName('d_' + trip.id + '_' + str(t))
            d_plus_1 = m.getVarByName('d_' + trip.id + '_' + str(t + 1))
            if d.X == 0 and d_plus_1.X == 1:
                trip.start_time = t + 1
                print('trip: ' + trip.id + '    start time: ' + str(t + 1))

    # output ticket validation start time
    for ticket_proto in ticket_dict:
        for ticket in ticket_dict[ticket_proto].values():
            for i in range(0, ticket_prototype_dict[ticket_proto].validation_number):
                for t in range(0, time_horizon_length - 1):
                    s = m.getVarByName('s_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t))
                    s_plus_1 = m.getVarByName(
                        's_' + ticket_proto + '_' + str(ticket.sequence) + '_' + str(i) + '_' + str(t + 1))
                    if s.X == 0 and s_plus_1.X == 1:
                        ticket.start_time[i] = t + 1
                        print('ticket type: ' + ticket_proto + '   validation:' + str(i) + '       start time:' + str(
                            t + 1))


def plot():
    trip_time = list()
    for trip in trip_dict.values():
        trip_time_stamp = (trip.start_time, trip.duration)
        trip_time.append(trip_time_stamp)

    fig, ax = plt.subplots()

    ax.broken_barh(trip_time, (7, 6), facecolors='#1f71ec')

    row_position = 15
    label_list = ['Trips']
    y_tick_list = [10]
    for ticket_proto in ticket_dict:
        for ticket in ticket_dict[ticket_proto].values():
            if len(ticket.start_time) == 0:
                continue
            validation_time = list()
            for i in range(0, ticket_prototype_dict[ticket_proto].validation_number):
                validation_time_stamp = (ticket.start_time[i], ticket.prototype.duration_per_validation)
                validation_time.append(validation_time_stamp)
            ax.broken_barh(validation_time, (row_position + 2, 6), facecolors='#f67a7a')
            label_list.append(ticket.prototype.type)
            y_tick_list.append(row_position + 5)
            row_position += 10

    ax.set_xlim(0, time_horizon_length)
    ax.set_xlabel('Time (h)')
    ax.set_xticks([24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 264, 288])

    ax.set_ylim(0, row_position + 5)
    ax.set_yticks(y_tick_list)
    ax.set_yticklabels(label_list)
    ax.grid(True)

    plt.savefig('fig.png', dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.show()


# main
read_trip_data()
read_ticket_data()

presolve()
solve()
