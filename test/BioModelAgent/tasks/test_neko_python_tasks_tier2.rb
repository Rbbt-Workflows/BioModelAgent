require File.expand_path('../../test_helper', __dir__)
require File.expand_path('../../../workflow.rb', __dir__)

class TestNekoPythonTasksTier2 < Test::Unit::TestCase
  TIER2 = %w[
    neko_remove_undefined_interactions
    neko_complete_connection
    neko_connect_targeted_nodes
    neko_bridge_components
    neko_filter_interactions
    neko_get_references
    neko_analyze_connectivity
    neko_analyze_gene_set
    neko_preview_connection_impact
  ].freeze

  def test_all_tier2_tasks_registered
    TIER2.each do |name|
      assert BioModelAgent.tasks.key?(name.to_sym),
             "task #{name} is not registered in BioModelAgent"
    end
  end

  def test_tier2_task_metadata_extracted
    TIER2.each do |name|
      info = BioModelAgent.task_info(name)
      inputs = info[:inputs]
      assert !inputs.empty?, "task #{name} exposes no inputs"
      names = inputs.map { |i| i.is_a?(Hash) ? i[:name] : i.to_s }
      assert names.include?('sif_path'), "task #{name} lacks a sif_path input"
    end
  end

  def test_tier2_task_descriptions_present
    TIER2.each do |name|
      description = BioModelAgent.tasks[name.to_sym].description.to_s
      assert !description.strip.empty?,
             "task #{name} produced an empty description"
    end
  end
end
