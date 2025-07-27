import pandas as pd
import requests
import json
import time
from web3 import Web3
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WalletRiskScorer:
    def __init__(self):
        # Initialize Web3 connection to Ethereum mainnet
        self.w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161'))
        
        # Compound V2 and V3 contract addresses
        self.compound_v2_addresses = [
            '0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B',  # Comptroller
            '0x5eAe89DC1C671724A672ff0630122ee834098657',  # Unitroller
        ]
        
        self.compound_v3_addresses = [
            '0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B',  # Comptroller
            '0x0d438F3b5175Bebee262F3e429D1497a7A3fA0C2',  # USDC Market
            '0x1b0e765F6224C21223AeA2af16c1C46E38885a40',  # ETH Market
        ]
        
        # Etherscan API key (you can get one for free)
        self.etherscan_api_key = os.getenv('ETHERSCAN_API_KEY', 'YourApiKeyToken')
        
        # Risk scoring weights
        self.risk_weights = {
            'transaction_frequency': 0.25,
            'total_volume': 0.20,
            'liquidation_events': 0.30,
            'collateral_ratio': 0.15,
            'protocol_interaction': 0.10
        }
    
    def get_transaction_history(self, wallet_address):
        """Fetch transaction history for a wallet address"""
        try:
            url = f"https://api.etherscan.io/api"
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': wallet_address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'desc',
                'apikey': self.etherscan_api_key
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == '1':
                    return data['result']
                else:
                    logger.warning(f"API Error for {wallet_address}: {data.get('message', 'Unknown error')}")
                    return []
            else:
                logger.error(f"HTTP Error for {wallet_address}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching transactions for {wallet_address}: {str(e)}")
            return []
    
    def filter_compound_transactions(self, transactions):
        """Filter transactions related to Compound protocol"""
        compound_transactions = []
        
        for tx in transactions:
            # Check if transaction involves Compound contracts
            to_address = tx.get('to', '').lower()
            from_address = tx.get('from', '').lower()
            
            # Compound V2 and V3 contract addresses (lowercase)
            compound_contracts = [
                '0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b',  # Comptroller
                '0x5eae89dc1c671724a672ff0630122ee834098657',  # Unitroller
                '0x0d438f3b5175bebee262f3e429d1497a7a3fa0c2',  # USDC Market
                '0x1b0e765f6224c21223aea2af16c1c46e38885a40',  # ETH Market
            ]
            
            if to_address in compound_contracts or from_address in compound_contracts:
                compound_transactions.append(tx)
        
        return compound_transactions
    
    def extract_features(self, wallet_address):
        """Extract risk features from wallet transactions"""
        logger.info(f"Processing wallet: {wallet_address}")
        
        # Get all transactions
        all_transactions = self.get_transaction_history(wallet_address)
        
        if not all_transactions:
            logger.warning(f"No transactions found for {wallet_address}")
            return self.get_default_features()
        
        # Filter Compound transactions
        compound_transactions = self.filter_compound_transactions(all_transactions)
        
        # Calculate features
        features = {}
        
        # 1. Transaction frequency (last 30 days)
        recent_transactions = [
            tx for tx in all_transactions 
            if int(tx.get('timeStamp', 0)) > (datetime.now() - timedelta(days=30)).timestamp()
        ]
        features['transaction_frequency'] = len(recent_transactions)
        
        # 2. Total volume (in ETH)
        total_volume = 0
        for tx in all_transactions:
            try:
                value_wei = int(tx.get('value', 0))
                value_eth = value_wei / 1e18
                total_volume += value_eth
            except:
                continue
        features['total_volume'] = total_volume
        
        # 3. Liquidation events (approximate based on failed transactions)
        liquidation_events = 0
        for tx in all_transactions:
            if tx.get('isError') == '1':
                liquidation_events += 1
        features['liquidation_events'] = liquidation_events
        
        # 4. Collateral ratio (approximate based on compound interactions)
        compound_interactions = len(compound_transactions)
        total_interactions = len(all_transactions)
        collateral_ratio = compound_interactions / max(total_interactions, 1)
        features['collateral_ratio'] = collateral_ratio
        
        # 5. Protocol interaction depth
        features['protocol_interaction'] = len(compound_transactions)
        
        logger.info(f"Features for {wallet_address}: {features}")
        return features
    
    def get_default_features(self):
        """Return default features for wallets with no transaction history"""
        return {
            'transaction_frequency': 0,
            'total_volume': 0,
            'liquidation_events': 0,
            'collateral_ratio': 0,
            'protocol_interaction': 0
        }
    
    def calculate_risk_score(self, features):
        """Calculate risk score from features (0-1000)"""
        # Normalize features to 0-1 range
        normalized_features = {}
        
        # Transaction frequency: 0-100 transactions -> 0-1
        normalized_features['transaction_frequency'] = min(features['transaction_frequency'] / 100, 1.0)
        
        # Total volume: 0-1000 ETH -> 0-1
        normalized_features['total_volume'] = min(features['total_volume'] / 1000, 1.0)
        
        # Liquidation events: 0-50 events -> 0-1
        normalized_features['liquidation_events'] = min(features['liquidation_events'] / 50, 1.0)
        
        # Collateral ratio: already 0-1
        normalized_features['collateral_ratio'] = features['collateral_ratio']
        
        # Protocol interaction: 0-100 interactions -> 0-1
        normalized_features['protocol_interaction'] = min(features['protocol_interaction'] / 100, 1.0)
        
        # Calculate weighted risk score
        risk_score = 0
        for feature, weight in self.risk_weights.items():
            risk_score += normalized_features[feature] * weight
        
        # Convert to 0-1000 scale
        final_score = int(risk_score * 1000)
        
        return final_score
    
    def process_wallets(self, input_file='wallet_id.xlsx', output_file='risk_scores.csv'):
        """Process all wallets and generate risk scores"""
        logger.info("Starting wallet risk scoring process...")
        
        # Read wallet addresses
        try:
            df = pd.read_excel(input_file)
            wallet_addresses = df['wallet_id'].tolist()
            logger.info(f"Loaded {len(wallet_addresses)} wallet addresses")
        except Exception as e:
            logger.error(f"Error reading input file: {str(e)}")
            return
        
        # Process each wallet
        results = []
        
        for i, wallet_address in enumerate(wallet_addresses):
            logger.info(f"Processing wallet {i+1}/{len(wallet_addresses)}: {wallet_address}")
            
            # Extract features
            features = self.extract_features(wallet_address)
            
            # Calculate risk score
            risk_score = self.calculate_risk_score(features)
            
            # Store result
            results.append({
                'wallet_id': wallet_address,
                'score': risk_score,
                'transaction_frequency': features['transaction_frequency'],
                'total_volume': features['total_volume'],
                'liquidation_events': features['liquidation_events'],
                'collateral_ratio': features['collateral_ratio'],
                'protocol_interaction': features['protocol_interaction']
            })
            
            # Rate limiting to avoid API limits
            time.sleep(0.2)
        
        # Create output DataFrame
        output_df = pd.DataFrame(results)
        
        # Save results
        output_df.to_csv(output_file, index=False)
        logger.info(f"Risk scores saved to {output_file}")
        
        # Print summary statistics
        logger.info(f"Risk Score Statistics:")
        logger.info(f"Mean: {output_df['score'].mean():.2f}")
        logger.info(f"Median: {output_df['score'].median():.2f}")
        logger.info(f"Min: {output_df['score'].min()}")
        logger.info(f"Max: {output_df['score'].max()}")
        
        return output_df

def main():
    """Main function to run the wallet risk scoring"""
    scorer = WalletRiskScorer()
    
    # Process wallets and generate risk scores
    results = scorer.process_wallets()
    
    if results is not None:
        print("\n=== WALLET RISK SCORING COMPLETE ===")
        print(f"Processed {len(results)} wallets")
        print("Results saved to 'risk_scores.csv'")
        
        # Display top 10 highest risk wallets
        print("\nTop 10 Highest Risk Wallets:")
        top_risk = results.nlargest(10, 'score')[['wallet_id', 'score']]
        print(top_risk.to_string(index=False))

if __name__ == "__main__":
    main() 