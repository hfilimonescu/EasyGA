from EasyGA import function_info
import random

# Round to an integer near x with higher probability
# the closer it is to that integer.
randround = lambda x: int(x + random.random())


@function_info
def _append_to_next_population(population_method):
    """Appends the new chromosomes to the next population.
    Also modifies the input to include the mating pool.
    """

    def new_method(ga):
        ga.population.append_children(
            population_method(ga, ga.population.mating_pool)
        )

    return new_method


@function_info
def _check_weight(individual_method):
    """Checks if the weight is between 0 and 1 before running.
    Exception may occur when using ga.adapt, which will catch
    the error and try again with valid weight.
    """

    def new_method(ga, parent_1, parent_2, *, weight = individual_method.__kwdefaults__.get('weight', None)):

        if weight is None:
            return individual_method(ga, parent_1, parent_2)
        elif 0 < weight < 1:
            return individual_method(ga, parent_1, parent_2, weight = weight)
        else:
            raise ValueError(f"Weight must be between 0 and 1 when using {individual_method.__name__}.")

    return new_method


class Crossover_Methods:

    # Allowing access to decorators when importing class
    _append_to_next_population = _append_to_next_population
    _check_weight              = _check_weight


    class Population:
        """Methods for selecting chromosomes to crossover."""


        @_append_to_next_population
        def sequential_selection(ga, mating_pool):
            """Select sequential pairs from the mating pool.
            Every parent is paired with the previous parent.
            The first parent is paired with the last parent.
            """
            
            for index in range(len(mating_pool)):    # for each parent in the mating pool
                yield ga.crossover_individual_impl(  #     apply crossover to
                    mating_pool[index],              #         the parent and
                    mating_pool[index-1],            #         the previous parent
                )


        @_append_to_next_population
        def random_selection(ga, mating_pool):
            """Select random pairs from the mating pool.
            Every parent is paired with a random parent.
            """

            for parent in mating_pool:               # for each parent in the mating pool
                yield ga.crossover_individual_impl(  #     apply crossover to
                    parent,                          #         the parent and
                    random.choice(mating_pool),      #         a random parent
                )


    class Individual:
        """Methods for crossing parents."""


        @_check_weight
        def single_point(ga, parent_1, parent_2, *, weight = 0.5):
            """Cross two parents by swapping genes at one random point."""

            minimum_parent_length = min(len(parent_1), len(parent_2))

            # Weighted random integer from 0 to minimum parent length - 1
            swap_index = int(ga.weighted_random(weight) * minimum_parent_length)

            # Randomly choose which parent's genes are selected first.
            if random.choice([True, False]):
                return parent_1[:swap_index] + parent_2[swap_index:]
            else:
                return parent_2[:-swap_index] + parent_1[-swap_index:]


        @_check_weight
        def multi_point(ga, parent_1, parent_2, *, weight = 0.5):
            """Cross two parents by swapping genes at multiple points."""
            pass


        @_check_weight
        def uniform(ga, parent_1, parent_2, *, weight = 0.5):
            """Cross two parents by swapping all genes randomly."""

            for gene_pair in zip(parent_1, parent_2):
                yield random.choices(gene_pair, cum_weights = [weight, 1])[0]


        class Arithmetic:
            """Crossover methods for numerical genes."""

            def average(ga, parent_1, parent_2, *, weight = 0.5):
                """Cross two parents by taking the average of the genes."""

                values_1 = parent_1.gene_value_iter
                values_2 = parent_2.gene_value_iter

                for value_1, value_2 in zip(values_1, values_2):

                    value = weight*value_1 + (1-weight)*value_2

                    if type(value_1) == type(value_2) == int:
                        value = randround(value)

                    yield value


            def extrapolate(ga, parent_1, parent_2, *, weight = 0.5):

                """Cross two parents by extrapolating towards the first parent.
                May result in gene values outside the expected domain.
                """

                values_1 = parent_1.gene_value_iter
                values_2 = parent_2.gene_value_iter

                for value_1, value_2 in zip(values_1, values_2):

                    value = (2-weight)*value_1 + (weight-1)*value_2

                    if type(value_1) == type(value_2) == int:
                        value = randround(value)

                    yield value


            @_check_weight
            def random(ga, parent_1, parent_2, *, weight = 0.5):
                """Cross two parents by taking a random integer or float value between each of the genes."""

                values_1 = parent_1.gene_value_iter
                values_2 = parent_2.gene_value_iter

                for value_1, value_2 in zip(values_1, values_2):

                    # Weighted random value between value 1 and value 2
                    value = value_1 + ga.weighted_random(weight) * (value_2-value_1)

                    if type(value_1) == type(value_2) == int:
                        value = randround(value)

                    yield value


        class Permutation:
            """Crossover methods for permutation based chromosomes."""

            @_check_weight
            def ox1(ga, parent_1, parent_2, *, weight = 0.5):
                """Cross two parents by slicing out a random part of one parent
                and then filling in the rest of the genes from the second parent."""

                # Too small to cross
                if len(parent_1) < 2:
                    return parent_1.gene_list

                # Unequal parent lengths
                if len(parent_1) != len(parent_2):
                    raise ValueError("Parents do not have the same lengths.")

                # Swap with weighted probability so that most of the genes
                # are taken directly from parent 1.
                if random.choices([0, 1], cum_weights = [weight, 1]) == 1:
                    parent_1, parent_2 = parent_2, parent_1

                # Extract genes from parent 1 between two random indexes
                index_2 = random.randrange(1, len(parent_1))
                index_1 = random.randrange(index_2)

                # Create copies of the gene lists
                gene_list_1 = [None]*index_1 + parent_1[index_1:index_2] + [None]*(len(parent_1)-index_2)
                gene_list_2 = list(parent_2)

                input_index = 0

                # For each gene from the second parent
                for _ in range(len(gene_list_2)):

                    # Remove it if it is already used
                    if gene_list_2[-1] in gene_list_1:
                        gene_list_2.pop(-1)

                    # Add it if it has not been used
                    else:
                        if input_index == index_1:
                            input_index = index_2
                        gene_list_1[input_index] = gene_list_2.pop(-1)
                        input_index += 1

                return gene_list_1


            @_check_weight
            def partially_mapped(ga, parent_1, parent_2, *, weight = 0.5):
                """Cross two parents by slicing out a random part of one parent
                and then filling in the rest of the genes from the second parent,
                preserving the ordering of genes wherever possible.

                NOTE: Needs to be fixed."""

                # Too small to cross
                if len(parent_1) < 2:
                    return parent_1.gene_list

                # Unequal parent lengths
                if len(parent_1) != len(parent_2):
                    raise ValueError("Parents do not have the same lengths.")

                # Swap with weighted probability so that most of the genes
                # are taken directly from parent 1.
                if random.choices([0, 1], cum_weights = [weight, 1]) == 1:
                    parent_1, parent_2 = parent_2, parent_1

                # Extract genes from parent 1 between two random indexes
                index_2 = random.randrange(1, len(parent_1))
                index_1 = random.randrange(index_2)

                # Create copies of the gene lists
                gene_list_1 = [None]*index_1 + parent_1[index_1:index_2] + [None]*(len(parent_1)-index_2)
                gene_list_2 = list(parent_2)

                # Create hash for gene list 2
                hash = {gene:index for index, gene in enumerate(gene_list_2)}

                # For each gene in the copied segment from parent 2
                for i in range(index_1, index_2):

                    # If it is not already copied,
                    # find where it got displaced to
                    j = i
                    while gene_list_1[(j := hash[gene_list_1[j]])] is not None:
                        pass
                    gene_list_1[j] = gene_list_2[i]

                # Fill in whatever is leftover (copied from ox1).
                # For each gene from the second parent
                for _ in range(len(gene_list_2)):

                    # Remove it if it is already used
                    if gene_list_2[-1] in gene_list_1:
                        gene_list_2.pop(-1)

                    # Add it if it has not been used
                    else:
                        if input_index == index_1:
                            input_index = index_2
                        gene_list_1[input_index] = gene_list_2.pop(-1)
                        input_index += 1

                return gene_list_1
