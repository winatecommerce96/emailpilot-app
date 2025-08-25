# ADR-001: LangChain Lab Sandboxed Integration

**Status**: Proposed  
**Date**: 2025-01-21  
**Deciders**: Development Team  
**Technical Story**: Evaluate LangChain for RAG and Agent capabilities  

## Context

EmailPilot currently uses a custom multi-agent orchestration system built with LangGraph. We want to evaluate LangChain's RAG (Retrieval-Augmented Generation) and Agent capabilities as potential enhancements or replacements for parts of our existing system.

Key requirements:
- Zero risk to existing production functionality
- Real-world evaluation with actual project data
- Easy rollback if evaluation is negative
- Minimal maintenance overhead during evaluation period

## Decision

We will implement LangChain capabilities as a completely sandboxed module called "LangChain Lab" with the following characteristics:

### Sandboxing Approach
1. **Isolated Module**: All LangChain code lives in `multi-agent/langchain_lab/`
2. **Optional Dependencies**: LangChain packages are marked as optional in requirements
3. **Graceful Degradation**: Core system continues to work if LangChain Lab is unavailable
4. **Read-Only Integration**: Lab can only read from existing systems, never write

### Integration Surface
1. **CLI Integration**: Optional `lc-rag` and `lc-agent` commands in orchestrator CLI
2. **Import Guards**: All LangChain imports wrapped in try/except blocks
3. **Feature Flags**: Environment variables control LangChain Lab activation
4. **Zero Core Changes**: No modifications to core EmailPilot application logic

### Evaluation Scope
1. **RAG Demo**: Document ingestion, vector search, grounded Q&A with citations
2. **Agent Demo**: Task-oriented agents with tool calling (Klaviyo, Firestore, calendar, web)
3. **Policy Framework**: Safety guardrails and resource limits
4. **Evaluation Framework**: Automated assessment of quality and performance

## Rationale

### Why Sandboxed Approach?
- **Risk Mitigation**: Zero chance of breaking existing functionality
- **Rapid Evaluation**: Can test with real data without production risk
- **Learning Opportunity**: Team gains LangChain experience safely
- **Flexibility**: Easy to expand or remove based on results

### Why These Specific Features?
- **RAG**: Complements existing knowledge management needs
- **Agents**: Could enhance or replace current multi-agent system
- **Policies**: Essential for production safety
- **Evaluation**: Data-driven decision making

### Alternative Approaches Considered
1. **Full Integration**: Too risky, would require major refactoring
2. **Separate Repository**: Harder to evaluate with real data
3. **Proof of Concept**: Too limited for real evaluation
4. **Branch-Based**: Harder to maintain and evaluate incrementally

## Consequences

### Positive
- **Zero Production Risk**: Core functionality remains untouched
- **Real-World Testing**: Can evaluate with actual EmailPilot data
- **Team Learning**: Builds LangChain expertise across the team
- **Future Options**: Creates foundation for potential migration
- **Competitive Analysis**: Helps understand LangChain ecosystem

### Negative
- **Additional Complexity**: More dependencies and code to maintain
- **Duplicate Functionality**: Some overlap with existing agent system
- **Maintenance Burden**: Need to keep LangChain Lab updated
- **Decision Overhead**: Need to choose between approaches for new features

### Neutral
- **Evaluation Period**: Expected 3-6 months for thorough assessment
- **Documentation**: Requires maintaining separate documentation
- **Testing**: Additional test suite for LangChain Lab components

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- [x] Module structure and configuration
- [x] Dependency management and guards
- [x] Basic CLI interface
- [x] Integration with orchestrator

### Phase 2: RAG Implementation (Week 2)
- [x] Document ingestion pipeline
- [x] Vector store management (FAISS/Chroma)
- [x] Q&A chains with citations
- [x] Response evaluation framework

### Phase 3: Agent Implementation (Week 3)
- [x] Tool definitions (Klaviyo, Firestore, calendar, web)
- [x] Policy enforcement framework
- [x] Agent execution and structured output
- [x] Safety guardrails and limits

### Phase 4: Evaluation & Testing (Week 4)
- [x] Comprehensive test suite
- [x] Documentation and examples
- [x] Validation scripts
- [x] Performance benchmarks

## Success Criteria

The LangChain Lab will be considered successful if it demonstrates:

### Performance Metrics
- **RAG Quality**: >85% faithfulness score on evaluation dataset
- **Agent Reliability**: <5% failure rate on standard tasks
- **Response Time**: <10s for typical RAG queries, <30s for agent tasks
- **Resource Efficiency**: Comparable or better than current system

### Adoption Metrics
- **Team Usage**: Regular use by 3+ team members
- **Use Cases**: Successfully handles 5+ real-world scenarios
- **Feedback**: Positive developer experience scores
- **Integration**: Smooth workflow integration without friction

### Technical Metrics
- **Stability**: No critical bugs in 1 month of testing
- **Maintainability**: Clear separation of concerns and good test coverage
- **Scalability**: Handles EmailPilot-scale data loads
- **Security**: Passes security review with no high-severity findings

## Promotion Criteria

LangChain Lab will be promoted to core functionality if:

1. **All success criteria are met** consistently over 3-month period
2. **Business value is demonstrated** through improved metrics or new capabilities
3. **Team consensus** supports migration based on experience
4. **Migration plan exists** with clear timeline and risk mitigation
5. **Backward compatibility** can be maintained during transition

## Rollback Plan

LangChain Lab can be safely removed by:

### Immediate Rollback (any time)
1. Remove orchestrator CLI integration calls
2. Set `LANGCHAIN_LAB_ENABLED=false` environment variable
3. System continues operating normally

### Complete Removal (if evaluation is negative)
1. Delete `multi-agent/langchain_lab/` directory
2. Remove LangChain dependencies from `requirements.txt`
3. Remove orchestrator integration code
4. Remove this ADR and related documentation

### Data Preservation
- All generated artifacts are saved to `artifacts/` directory
- Evaluation results preserved for future reference
- No data loss in core EmailPilot systems

## Monitoring and Review

### Weekly Reviews
- Usage metrics and adoption tracking
- Performance benchmarks and comparisons
- Bug reports and stability monitoring
- Developer feedback collection

### Monthly Assessment
- Success criteria evaluation
- Cost-benefit analysis update
- Technical debt assessment
- Decision point: continue, modify, or terminate

### Quarterly Decision Point
- Comprehensive evaluation against all criteria
- Go/no-go decision on promotion to core
- Resource allocation for next quarter
- Stakeholder approval for direction

## Dependencies

### External Dependencies
- LangChain ecosystem (langchain, langchain-openai, etc.)
- Vector stores (FAISS, optionally ChromaDB)
- LLM providers (OpenAI, Anthropic, Google)
- Embedding providers (OpenAI, Google Vertex, Sentence Transformers)

### Internal Dependencies
- Existing Firestore infrastructure
- Current orchestrator service
- EmailPilot authentication system
- Existing configuration management

### Risk Mitigation
- All external dependencies are optional
- Multiple provider options for each service
- Graceful degradation if services unavailable
- Regular dependency updates and security scanning

## Related Decisions

- **ADR-002**: TBD - Vector store selection (FAISS vs ChromaDB)
- **ADR-003**: TBD - LLM provider strategy and fallbacks
- **ADR-004**: TBD - Agent tool security model
- **ADR-005**: TBD - RAG evaluation methodology

## Notes

This ADR will be updated as we learn from the implementation and evaluation process. The sandboxed approach allows us to make these decisions incrementally with full context from real-world usage.