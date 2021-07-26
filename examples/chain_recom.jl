using GerryChain

SHAPEFILE_PATH = "./PA_VTDs.json"
POPULATION_COL = "TOTPOP"
ASSIGNMENT_COL = "CD_2011"

# Initialize graph and partition
graph = BaseGraph(SHAPEFILE_PATH, POPULATION_COL)
partition = Partition(graph, ASSIGNMENT_COL)

# Define parameters of chain (number of steps and population constraint)
pop_constraint = PopulationConstraint(graph, partition, 0.02)
num_steps = 1000

# Run the chain
for (partition, _) in recom_chain_iter(graph, partition, pop_constraint, num_steps, [DistrictAggregate("presd", "PRES12D"),], progress_bar=false)

    write(stdout, join(string.(partition.assignments), "\n"), "END\n")  # much faster?

    ## Alternatively, one could do: (slow)
    # for district in partition.assignments
    #     write(stdout, string(district, "\n")) # faster than println
    # end
    # write(stdout, "END\n") # faster than println

    ## Alternatively, one could do: (even slower)
    # for district in partition.assignments
    #     println(district)
    # end
    # println("END")
end
flush(stdout)
