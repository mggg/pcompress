using GerryChain

SHAPEFILE_PATH = "./PA_VTDs.json"
POPULATION_COL = "TOTPOP"
ASSIGNMENT_COL = "CD_2011"

# Initialize graph and partition
graph = BaseGraph(SHAPEFILE_PATH, POPULATION_COL)
partition = Partition(graph, ASSIGNMENT_COL)

# Define parameters of chain (number of steps and population constraint)
pop_constraint = PopulationConstraint(graph, partition, 0.02)
num_steps = 10000

# Run the chain
for (partition, _) in recom_chain_iter(graph, partition, pop_constraint, num_steps, [DistrictAggregate("presd", "PRES12D")])

    write(stdout, repr(partition.assignments .- 1), "\n")

    ## Alternatively, one could do: (slow)
    # show(repr(partition.assignments))

end
flush(stdout)
