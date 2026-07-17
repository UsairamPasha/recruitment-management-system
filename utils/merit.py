def calculate_merit(matric, inter, grad, master):
    division_scores = {'A': 85, 'B': 65, 'C': 50, 'D': 40}

    weights = {
        'matric': 0.25,
        'inter': 0.25,
        'grad': 0.30,
        'master': 0.20
    }

    # Ensure valid divisions
    try:
        merit = (
            division_scores[matric.upper()] * weights['matric'] +
            division_scores[inter.upper()] * weights['inter'] +
            division_scores[grad.upper()] * weights['grad'] +
            division_scores[master.upper()] * weights['master']
        )
    except KeyError:
        return 0  # Return 0 if any invalid division

    return round(merit, 2)
