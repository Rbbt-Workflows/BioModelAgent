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
BioModelAgent.tasks.keys.each{|t| BioModelAgent.export t }
