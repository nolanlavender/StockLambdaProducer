import json
import boto3
import logging
from datetime import datetime
from market_hours import MarketHours

logger = logging.getLogger()
logger.setLevel(logging.INFO)

stepfunctions_client = boto3.client('stepfunctions')

def lambda_handler(event, context):
    """
    EventBridge-triggered Lambda that controls Step Function execution
    Starts/stops based on market hours and other conditions
    Can be triggered by:
    1. Scheduled rule (every 30 min) - regular health check
    2. Step Function completion event - immediate restart for zero data loss
    """

    try:
        # Get Step Function ARN from environment
        import os
        state_machine_arn = os.getenv('STATE_MACHINE_ARN')
        if not state_machine_arn:
            raise ValueError("STATE_MACHINE_ARN environment variable not set")

        # Determine trigger source
        trigger_source = "scheduled"
        if event.get('detail-type') == 'Step Functions Execution Status Change':
            trigger_source = "completion"
            logger.info(f"🔔 Triggered by Step Function completion event")
        else:
            logger.info(f"⏰ Triggered by scheduled rule")

        market_hours = MarketHours()
        is_market_open, reason = market_hours.is_market_open()
        
        # Check current executions
        executions = stepfunctions_client.list_executions(
            stateMachineArn=state_machine_arn,
            statusFilter='RUNNING'
        )
        
        running_executions = executions.get('executions', [])
        is_currently_running = len(running_executions) > 0
        
        logger.info(f"Market status: {reason}")
        logger.info(f"Currently running executions: {len(running_executions)}")
        
        # Decision logic
        action_taken = "none"
        
        if is_market_open and not is_currently_running:
            # Market is open, but Step Function not running - START IT
            start_execution(state_machine_arn)
            action_taken = "started"
            logger.info("✅ Started Step Function - market is open")
            
        elif not is_market_open and is_currently_running:
            # Market is closed, but Step Function is running - STOP IT
            stop_running_executions(running_executions)
            action_taken = "stopped"
            logger.info("🛑 Stopped Step Function - market is closed")
            
        elif is_market_open and is_currently_running:
            # Market is open and Step Function is running - CONTINUE
            action_taken = "continued"
            logger.info("🔄 Step Function continues running - market is open")
            
        else:
            # Market is closed and Step Function is not running - DO NOTHING
            action_taken = "idle"
            logger.info("😴 Step Function remains idle - market is closed")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'trigger_source': trigger_source,
                'market_open': is_market_open,
                'market_reason': reason,
                'running_executions': len(running_executions),
                'action_taken': action_taken,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in Step Function controller: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }

def start_execution(state_machine_arn: str):
    """Start a new Step Function execution"""
    execution_name = f"market-session-{int(datetime.utcnow().timestamp())}"
    
    stepfunctions_client.start_execution(
        stateMachineArn=state_machine_arn,
        name=execution_name,
        input=json.dumps({
            'started_by': 'market_controller',
            'start_time': datetime.utcnow().isoformat()
        })
    )
    
    logger.info(f"Started execution: {execution_name}")

def stop_running_executions(executions: list):
    """Stop all running Step Function executions"""
    for execution in executions:
        try:
            stepfunctions_client.stop_execution(
                executionArn=execution['executionArn']
            )
            logger.info(f"Stopped execution: {execution['name']}")
        except Exception as e:
            logger.error(f"Failed to stop execution {execution['name']}: {e}")

def get_execution_status(state_machine_arn: str) -> dict:
    """Get detailed status of Step Function executions"""
    try:
        executions = stepfunctions_client.list_executions(
            stateMachineArn=state_machine_arn,
            maxResults=10
        )
        
        status_summary = {
            'running': 0,
            'succeeded': 0,
            'failed': 0,
            'aborted': 0,
            'total': len(executions.get('executions', []))
        }
        
        for execution in executions.get('executions', []):
            status = execution['status'].lower()
            if status in status_summary:
                status_summary[status] += 1
        
        return status_summary
        
    except Exception as e:
        logger.error(f"Failed to get execution status: {e}")
        return {}