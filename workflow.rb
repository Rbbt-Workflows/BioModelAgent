require 'scout'
require 'scout/workflow/python'

Misc.add_libdir if __FILE__ == $PROGRAM_NAME

module BioModelAgent
  extend Workflow
end

BioModelAgent.extend PythonWorkflow

# NeKo Tier 1 tasks (design note: doc/neko_python_tasks.md). Explicit file:
# paths are required because scout-rig 0.2.6 lacks Open.readpath, which the
# implicit python_task lookup would call.

BioModelAgent.python_task :neko_create_sif, file: File.expand_path('python/tasks/neko_create_sif.py', __dir__)
BioModelAgent.python_task :neko_add_nodes, file: File.expand_path('python/tasks/neko_add_nodes.py', __dir__)
BioModelAgent.python_task :neko_remove_genes, file: File.expand_path('python/tasks/neko_remove_genes.py', __dir__)
BioModelAgent.python_task :neko_remove_interaction, file: File.expand_path('python/tasks/neko_remove_interaction.py', __dir__)
BioModelAgent.python_task :neko_remove_bimodal_interactions, file: File.expand_path('python/tasks/neko_remove_bimodal_interactions.py', __dir__)
BioModelAgent.python_task :neko_network_report, file: File.expand_path('python/tasks/neko_network_report.py', __dir__)
BioModelAgent.python_task :neko_list_interactions, file: File.expand_path('python/tasks/neko_list_interactions.py', __dir__)
BioModelAgent.python_task :neko_find_paths, file: File.expand_path('python/tasks/neko_find_paths.py', __dir__)

# NeKo Tier 2 tasks (design note: doc/neko_python_tasks.md).

BioModelAgent.python_task :neko_remove_undefined_interactions, file: File.expand_path('python/tasks/neko_remove_undefined_interactions.py', __dir__)
BioModelAgent.python_task :neko_complete_connection, file: File.expand_path('python/tasks/neko_complete_connection.py', __dir__)
BioModelAgent.python_task :neko_connect_targeted_nodes, file: File.expand_path('python/tasks/neko_connect_targeted_nodes.py', __dir__)
BioModelAgent.python_task :neko_bridge_components, file: File.expand_path('python/tasks/neko_bridge_components.py', __dir__)
BioModelAgent.python_task :neko_filter_interactions, file: File.expand_path('python/tasks/neko_filter_interactions.py', __dir__)
BioModelAgent.python_task :neko_get_references, file: File.expand_path('python/tasks/neko_get_references.py', __dir__)
BioModelAgent.python_task :neko_analyze_connectivity, file: File.expand_path('python/tasks/neko_analyze_connectivity.py', __dir__)
BioModelAgent.python_task :neko_analyze_gene_set, file: File.expand_path('python/tasks/neko_analyze_gene_set.py', __dir__)
BioModelAgent.python_task :neko_preview_connection_impact, file: File.expand_path('python/tasks/neko_preview_connection_impact.py', __dir__)

BioModelAgent.extend LiveWorkflow
# MaBoSS tasks (design note: doc/maboss_python_tasks.md). Same explicit file:
# convention as the NeKo registrations above. The bundle convention (BND+CFG
# directory) is decided in doc/maboss_investigation.md (P5).

BioModelAgent.python_task :neko_export_bnet, file: File.expand_path('python/tasks/neko_export_bnet.py', __dir__)
BioModelAgent.python_task :maboss_bnet_to_bnd_cfg, file: File.expand_path('python/tasks/maboss_bnet_to_bnd_cfg.py', __dir__)
BioModelAgent.python_task :maboss_list_nodes, file: File.expand_path('python/tasks/maboss_list_nodes.py', __dir__)
BioModelAgent.python_task :maboss_get_initial_state, file: File.expand_path('python/tasks/maboss_get_initial_state.py', __dir__)
BioModelAgent.python_task :maboss_get_logical_rules, file: File.expand_path('python/tasks/maboss_get_logical_rules.py', __dir__)
BioModelAgent.python_task :maboss_get_mutations, file: File.expand_path('python/tasks/maboss_get_mutations.py', __dir__)
BioModelAgent.python_task :maboss_get_parameters, file: File.expand_path('python/tasks/maboss_get_parameters.py', __dir__)
BioModelAgent.python_task :maboss_change_rule, file: File.expand_path('python/tasks/maboss_change_rule.py', __dir__)
BioModelAgent.python_task :maboss_update_parameters, file: File.expand_path('python/tasks/maboss_update_parameters.py', __dir__)
BioModelAgent.python_task :maboss_set_output_nodes, file: File.expand_path('python/tasks/maboss_set_output_nodes.py', __dir__)
BioModelAgent.python_task :maboss_set_initial_state, file: File.expand_path('python/tasks/maboss_set_initial_state.py', __dir__)
BioModelAgent.python_task :maboss_run_simulation, file: File.expand_path('python/tasks/maboss_run_simulation.py', __dir__)
BioModelAgent.python_task :maboss_simulate_mutation, file: File.expand_path('python/tasks/maboss_simulate_mutation.py', __dir__)
BioModelAgent.python_task :maboss_plot_trajectories, file: File.expand_path('python/tasks/maboss_plot_trajectories.py', __dir__)
BioModelAgent.python_task :maboss_check, file: File.expand_path('python/tasks/maboss_check.py', __dir__)

BioModelAgent.tasks.keys.each{|t| BioModelAgent.export t }
